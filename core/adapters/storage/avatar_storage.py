"""
头像存储适配器
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
import hashlib
import aiofiles
import magic
from PIL import Image
import io

from core.config import settings


class AvatarStorageAdapter:
    """头像存储适配器"""
    
    def __init__(self):
        self.storage_type = getattr(settings, 'AVATAR_STORAGE_TYPE', 'local')
        self.max_size_mb = getattr(settings, 'AVATAR_MAX_SIZE_MB', 5)
        self.allowed_types = getattr(settings, 'AVATAR_ALLOWED_TYPES', ['jpg', 'jpeg', 'png', 'gif'])
        self.base_path = Path(getattr(settings, 'AVATAR_STORAGE_PATH', './storage/avatars'))
        
        # 确保存储目录存在
        if self.storage_type == 'local':
            self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save_avatar(
        self,
        user_id: str,
        file_data: bytes,
        file_name: str
    ) -> Tuple[str, str]:
        """
        保存头像文件
        返回: (存储路径, 访问URL)
        """
        # 验证文件
        is_valid, error_msg = await self._validate_file(file_data, file_name)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 处理图片（调整大小、优化）
        processed_data = await self._process_image(file_data)
        
        # 生成文件路径
        file_hash = hashlib.md5(processed_data).hexdigest()
        ext = Path(file_name).suffix.lower()
        storage_name = f"{file_hash}{ext}"
        
        # 根据存储类型保存
        if self.storage_type == 'local':
            return await self._save_local(user_id, processed_data, storage_name)
        else:
            # 可以扩展支持S3、OSS等云存储
            raise NotImplementedError(f"Storage type {self.storage_type} not implemented")
    
    async def delete_avatar(self, user_id: str, file_path: str) -> bool:
        """删除头像文件"""
        if self.storage_type == 'local':
            return await self._delete_local(user_id, file_path)
        else:
            raise NotImplementedError(f"Storage type {self.storage_type} not implemented")
    
    async def get_avatar_url(self, file_path: str) -> str:
        """获取头像访问URL"""
        if self.storage_type == 'local':
            # 本地存储返回相对路径，需要配合静态文件服务
            return f"/static/avatars{file_path}"
        else:
            # 云存储返回完整URL
            return file_path
    
    async def _validate_file(self, file_data: bytes, file_name: str) -> Tuple[bool, Optional[str]]:
        """验证文件"""
        # 检查文件大小
        file_size_mb = len(file_data) / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            return False, f"文件大小超过限制 {self.max_size_mb}MB"
        
        # 检查文件类型（通过文件内容）
        file_type = magic.from_buffer(file_data, mime=True)
        allowed_mimes = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif'
        }
        
        if file_type not in allowed_mimes.values():
            return False, f"不支持的文件类型: {file_type}"
        
        # 检查文件扩展名
        ext = Path(file_name).suffix.lower()[1:]  # 去掉点号
        if ext not in self.allowed_types:
            return False, f"不支持的文件扩展名: {ext}"
        
        return True, None
    
    async def _process_image(self, file_data: bytes) -> bytes:
        """处理图片（调整大小、优化）"""
        # 打开图片
        image = Image.open(io.BytesIO(file_data))
        
        # 转换为RGB（如果需要）
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        
        # 限制最大尺寸
        max_size = (500, 500)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 保存到字节流
        output = io.BytesIO()
        
        # 根据原始格式保存
        if image.format == 'PNG':
            image.save(output, format='PNG', optimize=True)
        else:
            # 默认保存为JPEG
            if image.mode == 'RGBA':
                # 处理透明背景
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            image.save(output, format='JPEG', quality=85, optimize=True)
        
        return output.getvalue()
    
    async def _save_local(
        self,
        user_id: str,
        file_data: bytes,
        file_name: str
    ) -> Tuple[str, str]:
        """保存到本地存储"""
        # 创建用户目录
        user_dir = self.base_path / user_id
        user_dir.mkdir(exist_ok=True)
        
        # 保存文件
        file_path = user_dir / file_name
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_data)
        
        # 返回相对路径
        relative_path = f"/{user_id}/{file_name}"
        access_url = await self.get_avatar_url(relative_path)
        
        return str(relative_path), access_url
    
    async def _delete_local(self, user_id: str, file_path: str) -> bool:
        """从本地存储删除"""
        try:
            # 构建完整路径
            if file_path.startswith('/'):
                file_path = file_path[1:]
            
            full_path = self.base_path / file_path
            
            # 删除文件
            if full_path.exists():
                full_path.unlink()
                
                # 如果用户目录为空，删除目录
                user_dir = full_path.parent
                if not any(user_dir.iterdir()):
                    user_dir.rmdir()
                
                return True
            
            return False
            
        except Exception:
            return False
    
    async def cleanup_user_avatars(self, user_id: str) -> int:
        """清理用户的所有头像（保留最新的）"""
        if self.storage_type != 'local':
            raise NotImplementedError(f"Cleanup not implemented for {self.storage_type}")
        
        user_dir = self.base_path / user_id
        if not user_dir.exists():
            return 0
        
        # 获取所有文件，按修改时间排序
        files = sorted(user_dir.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)
        
        # 保留最新的一个，删除其他
        deleted_count = 0
        for file in files[1:]:  # 跳过第一个（最新的）
            file.unlink()
            deleted_count += 1
        
        return deleted_count