"""
数据备份管理器 - 自动备份和恢复功能
"""

import os
import gzip
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import subprocess
import tempfile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# 条件导入boto3
try:
    import boto3
    from botocore.exceptions import NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    NoCredentialsError = Exception
    BOTO3_AVAILABLE = False

from core.config import settings
from core.database.session import get_db

logger = logging.getLogger(__name__)


class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.backup_dir = Path(settings.backup_directory or "./backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.s3_client = None
        self.max_local_backups = 7  # 本地保留7天备份
        self.max_s3_backups = 30    # S3保留30天备份
        
        # 初始化S3客户端
        if (BOTO3_AVAILABLE and 
            all([getattr(settings, 'aws_access_key_id', None), 
                 getattr(settings, 'aws_secret_access_key', None), 
                 getattr(settings, 's3_backup_bucket', None)])):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=getattr(settings, 'aws_access_key_id', None),
                    aws_secret_access_key=getattr(settings, 'aws_secret_access_key', None),
                    region_name=getattr(settings, 'aws_region', 'us-east-1')
                )
                logger.info("✅ S3备份客户端初始化成功")
            except Exception as e:
                logger.warning(f"S3备份客户端初始化失败: {e}")
        elif not BOTO3_AVAILABLE:
            logger.info("boto3未安装，S3备份功能不可用")
                
    async def create_full_backup(self, include_analysis_data: bool = True) -> Dict[str, Any]:
        """
        创建完整数据备份
        
        Args:
            include_analysis_data: 是否包含分析数据（可能很大）
        """
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_info = {
            "backup_id": backup_id,
            "timestamp": datetime.now().isoformat(),
            "type": "full",
            "include_analysis_data": include_analysis_data,
            "files": [],
            "size": 0,
            "status": "in_progress"
        }
        
        try:
            # 1. 备份PostgreSQL数据库
            logger.info("开始备份PostgreSQL数据库...")
            db_backup_file = await self._backup_postgresql(backup_id, include_analysis_data)
            if db_backup_file:
                backup_info["files"].append({
                    "type": "postgresql",
                    "file": str(db_backup_file),
                    "size": os.path.getsize(db_backup_file)
                })
                
            # 2. 备份Redis缓存（如果需要）
            if settings.backup_redis:
                logger.info("开始备份Redis缓存...")
                redis_backup_file = await self._backup_redis(backup_id)
                if redis_backup_file:
                    backup_info["files"].append({
                        "type": "redis",
                        "file": str(redis_backup_file),
                        "size": os.path.getsize(redis_backup_file)
                    })
                    
            # 3. 备份配置文件
            logger.info("开始备份配置文件...")
            config_backup_file = await self._backup_configurations(backup_id)
            if config_backup_file:
                backup_info["files"].append({
                    "type": "config",
                    "file": str(config_backup_file),
                    "size": os.path.getsize(config_backup_file)
                })
                
            # 4. 计算总大小
            backup_info["size"] = sum(f["size"] for f in backup_info["files"])
            
            # 5. 创建备份清单文件
            manifest_file = self.backup_dir / f"backup_{backup_id}_manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
                
            # 6. 上传到S3（如果配置了）
            if self.s3_client:
                await self._upload_to_s3(backup_info)
                
            # 7. 清理旧备份
            await self._cleanup_old_backups()
            
            backup_info["status"] = "completed"
            logger.info(f"✅ 备份完成: {backup_id}, 总大小: {backup_info['size'] / 1024 / 1024:.2f}MB")
            
        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            logger.error(f"❌ 备份失败: {e}")
            
        return backup_info
        
    async def _backup_postgresql(self, backup_id: str, include_analysis_data: bool) -> Optional[Path]:
        """备份PostgreSQL数据库"""
        try:
            backup_file = self.backup_dir / f"postgres_{backup_id}.sql.gz"
            
            # 构建pg_dump命令
            cmd = [
                "pg_dump",
                "--host", settings.database_host,
                "--port", str(settings.database_port),
                "--username", settings.database_user,
                "--dbname", settings.database_name,
                "--no-password",
                "--verbose",
                "--format", "custom",
                "--compress", "9"
            ]
            
            # 如果不包含分析数据，排除相关表
            if not include_analysis_data:
                cmd.extend([
                    "--exclude-table", "analysis_tasks",
                    "--exclude-table", "analysis_reports", 
                    "--exclude-table", "analysis_logs"
                ])
                
            # 设置环境变量
            env = os.environ.copy()
            env["PGPASSWORD"] = settings.database_password
            
            # 执行备份命令
            with open(backup_file, 'wb') as f:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=3600  # 1小时超时
                )
                
                if result.returncode == 0:
                    # 压缩备份文件
                    with gzip.open(f, 'wb') as gz_f:
                        gz_f.write(result.stdout)
                    logger.info(f"PostgreSQL备份成功: {backup_file}")
                    return backup_file
                else:
                    logger.error(f"PostgreSQL备份失败: {result.stderr.decode()}")
                    return None
                    
        except Exception as e:
            logger.error(f"PostgreSQL备份异常: {e}")
            return None
            
    async def _backup_redis(self, backup_id: str) -> Optional[Path]:
        """备份Redis数据"""
        try:
            from core.cache.manager import cache_manager
            
            if not cache_manager.redis_client:
                logger.warning("Redis客户端未初始化，跳过Redis备份")
                return None
                
            backup_file = self.backup_dir / f"redis_{backup_id}.json.gz"
            
            # 获取所有键
            keys = await cache_manager.redis_client.keys(f"{cache_manager.prefix}*")
            
            redis_data = {}
            for key in keys:
                try:
                    key_str = key.decode('utf-8')
                    value = await cache_manager.redis_client.get(key)
                    ttl = await cache_manager.redis_client.ttl(key)
                    
                    redis_data[key_str] = {
                        "value": value.decode('utf-8') if value else None,
                        "ttl": ttl if ttl > 0 else None
                    }
                except Exception as e:
                    logger.warning(f"备份Redis键失败 {key}: {e}")
                    
            # 压缩保存
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                json.dump(redis_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Redis备份成功: {backup_file}, 键数量: {len(redis_data)}")
            return backup_file
            
        except Exception as e:
            logger.error(f"Redis备份异常: {e}")
            return None
            
    async def _backup_configurations(self, backup_id: str) -> Optional[Path]:
        """备份配置文件"""
        try:
            backup_file = self.backup_dir / f"config_{backup_id}.json.gz"
            
            config_data = {
                "timestamp": datetime.now().isoformat(),
                "app_version": getattr(settings, 'app_version', '1.0.0'),
                "settings": {
                    # 只备份非敏感配置
                    "database_host": settings.database_host,
                    "database_port": settings.database_port,
                    "database_name": settings.database_name,
                    "redis_host": settings.redis_host,
                    "redis_port": settings.redis_port,
                    "jwt_expiration_hours": settings.jwt_expiration_hours,
                    # 不备份密码和密钥
                }
            }
            
            # 添加环境变量（非敏感）
            env_vars = {}
            for key, value in os.environ.items():
                if not any(sensitive in key.upper() for sensitive in 
                          ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
                    env_vars[key] = value
                    
            config_data["environment"] = env_vars
            
            # 压缩保存
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"配置备份成功: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"配置备份异常: {e}")
            return None
            
    async def _upload_to_s3(self, backup_info: Dict[str, Any]):
        """上传备份到S3"""
        if not self.s3_client:
            return
            
        try:
            bucket = settings.s3_backup_bucket
            backup_id = backup_info["backup_id"]
            
            for file_info in backup_info["files"]:
                file_path = Path(file_info["file"])
                s3_key = f"backups/{backup_id}/{file_path.name}"
                
                # 上传文件
                self.s3_client.upload_file(
                    str(file_path),
                    bucket,
                    s3_key,
                    ExtraArgs={
                        'StorageClass': 'STANDARD_IA',  # 使用低频访问存储类
                        'ServerSideEncryption': 'AES256'
                    }
                )
                
                logger.info(f"文件上传到S3成功: {s3_key}")
                
            # 上传清单文件
            manifest_file = self.backup_dir / f"backup_{backup_id}_manifest.json"
            s3_manifest_key = f"backups/{backup_id}/manifest.json"
            self.s3_client.upload_file(
                str(manifest_file),
                bucket,
                s3_manifest_key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"✅ 备份上传S3完成: {backup_id}")
            
        except Exception as e:
            logger.error(f"S3上传失败: {e}")
            
    async def _cleanup_old_backups(self):
        """清理旧备份"""
        try:
            # 清理本地旧备份
            backup_files = list(self.backup_dir.glob("backup_*_manifest.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(backup_files) > self.max_local_backups:
                for manifest_file in backup_files[self.max_local_backups:]:
                    try:
                        # 读取备份信息
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            backup_info = json.load(f)
                            
                        # 删除备份文件
                        for file_info in backup_info.get("files", []):
                            file_path = Path(file_info["file"])
                            if file_path.exists():
                                file_path.unlink()
                                
                        # 删除清单文件
                        manifest_file.unlink()
                        logger.info(f"删除旧备份: {backup_info['backup_id']}")
                        
                    except Exception as e:
                        logger.error(f"删除旧备份失败: {e}")
                        
            # 清理S3旧备份
            if self.s3_client:
                await self._cleanup_s3_backups()
                
        except Exception as e:
            logger.error(f"清理旧备份异常: {e}")
            
    async def _cleanup_s3_backups(self):
        """清理S3旧备份"""
        try:
            bucket = settings.s3_backup_bucket
            cutoff_date = datetime.now() - timedelta(days=self.max_s3_backups)
            
            # 列出所有备份
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix="backups/"
            )
            
            if 'Contents' not in response:
                return
                
            # 按日期分组
            backup_dates = {}
            for obj in response['Contents']:
                key = obj['Key']
                last_modified = obj['LastModified'].replace(tzinfo=None)
                
                if last_modified < cutoff_date:
                    # 删除过期备份
                    self.s3_client.delete_object(Bucket=bucket, Key=key)
                    logger.info(f"删除S3旧备份: {key}")
                    
        except Exception as e:
            logger.error(f"清理S3旧备份异常: {e}")
            
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        try:
            # 本地备份
            manifest_files = list(self.backup_dir.glob("backup_*_manifest.json"))
            
            for manifest_file in manifest_files:
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                        backup_info["location"] = "local"
                        backups.append(backup_info)
                except Exception as e:
                    logger.error(f"读取备份清单失败 {manifest_file}: {e}")
                    
            # S3备份（如果配置了）
            if self.s3_client:
                try:
                    s3_backups = await self._list_s3_backups()
                    backups.extend(s3_backups)
                except Exception as e:
                    logger.error(f"列出S3备份失败: {e}")
                    
            # 按时间排序
            backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
        except Exception as e:
            logger.error(f"列出备份异常: {e}")
            
        return backups
        
    async def _list_s3_backups(self) -> List[Dict[str, Any]]:
        """列出S3备份"""
        backups = []
        
        try:
            bucket = settings.s3_backup_bucket
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix="backups/",
                Delimiter="/"
            )
            
            for prefix in response.get('CommonPrefixes', []):
                backup_id = prefix['Prefix'].split('/')[-2]
                
                # 尝试获取清单文件
                try:
                    manifest_key = f"backups/{backup_id}/manifest.json"
                    obj = self.s3_client.get_object(Bucket=bucket, Key=manifest_key)
                    backup_info = json.loads(obj['Body'].read().decode('utf-8'))
                    backup_info["location"] = "s3"
                    backups.append(backup_info)
                except:
                    # 如果没有清单文件，创建基础信息
                    backups.append({
                        "backup_id": backup_id,
                        "location": "s3",
                        "type": "unknown"
                    })
                    
        except Exception as e:
            logger.error(f"列出S3备份异常: {e}")
            
        return backups
        
    async def restore_backup(self, backup_id: str, restore_options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID
            restore_options: 恢复选项 {"database": True, "redis": True, "config": True}
        """
        if restore_options is None:
            restore_options = {"database": True, "redis": True, "config": False}
            
        restore_info = {
            "backup_id": backup_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "restored_components": []
        }
        
        try:
            # 查找备份清单
            manifest_file = self.backup_dir / f"backup_{backup_id}_manifest.json"
            
            if not manifest_file.exists():
                # 尝试从S3下载
                if self.s3_client:
                    await self._download_from_s3(backup_id)
                    
            if not manifest_file.exists():
                raise FileNotFoundError(f"备份清单文件不存在: {backup_id}")
                
            # 读取备份清单
            with open(manifest_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
                
            # 恢复各个组件
            for file_info in backup_info.get("files", []):
                component_type = file_info["type"]
                
                if component_type == "postgresql" and restore_options.get("database"):
                    success = await self._restore_postgresql(file_info["file"])
                    if success:
                        restore_info["restored_components"].append("database")
                        
                elif component_type == "redis" and restore_options.get("redis"):
                    success = await self._restore_redis(file_info["file"])
                    if success:
                        restore_info["restored_components"].append("redis")
                        
                elif component_type == "config" and restore_options.get("config"):
                    success = await self._restore_config(file_info["file"])
                    if success:
                        restore_info["restored_components"].append("config")
                        
            restore_info["status"] = "completed"
            logger.info(f"✅ 备份恢复完成: {backup_id}")
            
        except Exception as e:
            restore_info["status"] = "failed"
            restore_info["error"] = str(e)
            logger.error(f"❌ 备份恢复失败: {e}")
            
        return restore_info
        
    async def _restore_postgresql(self, backup_file: str) -> bool:
        """恢复PostgreSQL数据库"""
        try:
            # 这里应该实现PostgreSQL恢复逻辑
            # 注意：这是危险操作，需要仔细实现
            logger.warning("PostgreSQL恢复功能需要手动实现")
            return False
            
        except Exception as e:
            logger.error(f"PostgreSQL恢复异常: {e}")
            return False
            
    async def _restore_redis(self, backup_file: str) -> bool:
        """恢复Redis数据"""
        try:
            from core.cache.manager import cache_manager
            
            if not cache_manager.redis_client:
                logger.error("Redis客户端未初始化")
                return False
                
            # 读取备份数据
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                redis_data = json.load(f)
                
            # 恢复数据
            for key, data in redis_data.items():
                value = data["value"]
                ttl = data.get("ttl")
                
                if value is not None:
                    if ttl:
                        await cache_manager.redis_client.setex(key, ttl, value)
                    else:
                        await cache_manager.redis_client.set(key, value)
                        
            logger.info(f"✅ Redis数据恢复完成，恢复键数量: {len(redis_data)}")
            return True
            
        except Exception as e:
            logger.error(f"Redis恢复异常: {e}")
            return False
            
    async def _restore_config(self, backup_file: str) -> bool:
        """恢复配置文件"""
        try:
            # 配置恢复需要谨慎处理，通常只做参考
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                config_data = json.load(f)
                
            logger.info(f"配置备份信息: {config_data.get('timestamp')}")
            logger.info("配置恢复完成（仅供参考）")
            return True
            
        except Exception as e:
            logger.error(f"配置恢复异常: {e}")
            return False
            
    async def _download_from_s3(self, backup_id: str):
        """从S3下载备份"""
        if not self.s3_client:
            return
            
        try:
            bucket = settings.s3_backup_bucket
            
            # 下载清单文件
            manifest_key = f"backups/{backup_id}/manifest.json"
            local_manifest = self.backup_dir / f"backup_{backup_id}_manifest.json"
            
            self.s3_client.download_file(bucket, manifest_key, str(local_manifest))
            
            # 读取清单并下载所有文件
            with open(local_manifest, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
                
            for file_info in backup_info.get("files", []):
                s3_key = f"backups/{backup_id}/{Path(file_info['file']).name}"
                local_file = self.backup_dir / Path(file_info["file"]).name
                
                self.s3_client.download_file(bucket, s3_key, str(local_file))
                # 更新本地文件路径
                file_info["file"] = str(local_file)
                
            # 更新清单文件
            with open(local_manifest, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
                
            logger.info(f"✅ 从S3下载备份完成: {backup_id}")
            
        except Exception as e:
            logger.error(f"从S3下载备份失败: {e}")
            
    async def schedule_backup(self):
        """定时备份任务"""
        while True:
            try:
                # 每天凌晨2点执行备份
                now = datetime.now()
                next_backup = now.replace(hour=2, minute=0, second=0, microsecond=0)
                
                if next_backup <= now:
                    next_backup += timedelta(days=1)
                    
                wait_seconds = (next_backup - now).total_seconds()
                logger.info(f"下次备份时间: {next_backup}, 等待: {wait_seconds}秒")
                
                await asyncio.sleep(wait_seconds)
                
                # 执行备份
                logger.info("开始定时备份...")
                backup_info = await self.create_full_backup(include_analysis_data=False)
                
                if backup_info["status"] == "completed":
                    logger.info("✅ 定时备份完成")
                else:
                    logger.error("❌ 定时备份失败")
                    
            except Exception as e:
                logger.error(f"定时备份异常: {e}")
                await asyncio.sleep(3600)  # 发生错误时等待1小时再试


# 全局备份管理器实例
backup_manager = BackupManager()