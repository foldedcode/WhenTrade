"""
数据处理管道

集成不同数据源，处理、清洗、验证和转换数据
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Type
from datetime import datetime, date
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

from core.adapters.base import (
    DataRequest, DataResponse, DataPoint, DataType, DataFrequency
)
# from core.data_source_registry import global_data_source_registry  # TODO: 需要修复缺失的依赖

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """管道配置"""
    enable_validation: bool = True
    enable_cleaning: bool = True
    enable_transformation: bool = True
    enable_aggregation: bool = True
    max_retries: int = 3
    timeout: int = 30
    cache_results: bool = True
    parallel_processing: bool = True
    quality_threshold: float = 0.8  # 数据质量阈值


@dataclass
class PipelineResult:
    """管道处理结果"""
    success: bool
    data: pd.DataFrame
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    data_quality_score: float = 0.0
    source_count: int = 0


class DataProcessor(ABC):
    """数据处理器基类"""
    
    @abstractmethod
    async def process(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """处理数据"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取处理器名称"""
        pass


class DataValidator(DataProcessor):
    """数据验证器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.required_columns = self.config.get('required_columns', ['symbol', 'timestamp', 'value'])
        self.allow_null_percentage = self.config.get('allow_null_percentage', 0.1)
        self.min_data_points = self.config.get('min_data_points', 1)
    
    async def process(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """验证数据质量"""
        if data.empty:
            raise ValueError("Empty dataset")
        
        # 检查必需列
        missing_columns = set(self.required_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # 检查数据点数量
        if len(data) < self.min_data_points:
            raise ValueError(f"Insufficient data points: {len(data)} < {self.min_data_points}")
        
        # 检查空值比例
        for col in self.required_columns:
            null_ratio = data[col].isnull().sum() / len(data)
            if null_ratio > self.allow_null_percentage:
                raise ValueError(f"Too many null values in {col}: {null_ratio:.2%}")
        
        # 验证时间戳
        if 'timestamp' in data.columns:
            try:
                pd.to_datetime(data['timestamp'])
            except:
                raise ValueError("Invalid timestamp format")
        
        # 验证数值
        if 'value' in data.columns:
            if not pd.api.types.is_numeric_dtype(data['value']):
                try:
                    data['value'] = pd.to_numeric(data['value'], errors='coerce')
                except:
                    raise ValueError("Invalid numeric values")
        
        metadata['validation_passed'] = True
        return data
    
    def get_name(self) -> str:
        return "DataValidator"


class DataCleaner(DataProcessor):
    """数据清洗器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.remove_duplicates = self.config.get('remove_duplicates', True)
        self.fill_missing = self.config.get('fill_missing', True)
        self.remove_outliers = self.config.get('remove_outliers', True)
        self.outlier_threshold = self.config.get('outlier_threshold', 3.0)  # 标准差倍数
    
    async def process(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """清洗数据"""
        original_count = len(data)
        
        # 移除重复项
        if self.remove_duplicates:
            data = data.drop_duplicates()
            logger.info(f"Removed {original_count - len(data)} duplicate rows")
        
        # 处理缺失值
        if self.fill_missing:
            # 对数值列使用前向填充
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            data[numeric_columns] = data[numeric_columns].ffill()
            
            # 对其他列使用众数填充
            for col in data.columns:
                if data[col].dtype == 'object' and data[col].isnull().any():
                    mode_value = data[col].mode()
                    if not mode_value.empty:
                        data[col] = data[col].fillna(mode_value[0])
        
        # 移除异常值
        if self.remove_outliers and 'value' in data.columns:
            if pd.api.types.is_numeric_dtype(data['value']):
                mean = data['value'].mean()
                std = data['value'].std()
                threshold = self.outlier_threshold * std
                
                outlier_mask = np.abs(data['value'] - mean) > threshold
                outlier_count = outlier_mask.sum()
                
                if outlier_count > 0:
                    data = data[~outlier_mask]
                    logger.info(f"Removed {outlier_count} outliers")
        
        metadata['cleaning_stats'] = {
            'original_count': original_count,
            'final_count': len(data),
            'removed_count': original_count - len(data)
        }
        
        return data
    
    def get_name(self) -> str:
        return "DataCleaner"


class DataTransformer(DataProcessor):
    """数据转换器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.normalize_timestamps = self.config.get('normalize_timestamps', True)
        self.sort_by_time = self.config.get('sort_by_time', True)
        self.standardize_columns = self.config.get('standardize_columns', True)
    
    async def process(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """转换数据格式"""
        # 标准化时间戳
        if self.normalize_timestamps and 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            if self.sort_by_time:
                data = data.sort_values('timestamp')
        
        # 标准化列名
        if self.standardize_columns:
            column_mapping = {
                'time': 'timestamp',
                'datetime': 'timestamp',
                'price': 'value',
                'close': 'value',
                'last': 'value'
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in data.columns and new_name not in data.columns:
                    data = data.rename(columns={old_name: new_name})
        
        # 确保必需列存在
        required_columns = ['symbol', 'timestamp', 'value']
        for col in required_columns:
            if col not in data.columns:
                if col == 'symbol' and 'symbol' not in metadata:
                    data[col] = metadata.get('default_symbol', 'UNKNOWN')
                elif col == 'timestamp':
                    data[col] = datetime.now()
                elif col == 'value':
                    logger.warning(f"Missing value column, using 0 as default")
                    data[col] = 0.0
        
        metadata['transformation_applied'] = True
        return data
    
    def get_name(self) -> str:
        return "DataTransformer"


class DataAggregator(DataProcessor):
    """数据聚合器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.group_by_symbol = self.config.get('group_by_symbol', True)
        self.resample_frequency = self.config.get('resample_frequency', None)
        self.aggregation_methods = self.config.get('aggregation_methods', {
            'value': 'last',
            'volume': 'sum'
        })
    
    async def process(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """聚合数据"""
        if data.empty:
            return data
        
        # 按频率重采样
        if self.resample_frequency and 'timestamp' in data.columns:
            if not isinstance(data.index, pd.DatetimeIndex):
                data = data.set_index('timestamp')
            
            # 按symbol分组聚合
            if self.group_by_symbol and 'symbol' in data.columns:
                aggregated_dfs = []
                for symbol in data['symbol'].unique():
                    symbol_data = data[data['symbol'] == symbol]
                    resampled = symbol_data.resample(self.resample_frequency).agg(self.aggregation_methods)
                    resampled['symbol'] = symbol
                    aggregated_dfs.append(resampled)
                
                data = pd.concat(aggregated_dfs, ignore_index=True)
            else:
                data = data.resample(self.resample_frequency).agg(self.aggregation_methods)
        
        metadata['aggregation_applied'] = True
        return data
    
    def get_name(self) -> str:
        return "DataAggregator"


class DataPipeline:
    """数据处理管道"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.processors: List[DataProcessor] = []
        self.setup_default_processors()
    
    def setup_default_processors(self):
        """设置默认处理器"""
        if self.config.enable_validation:
            self.add_processor(DataValidator())
        
        if self.config.enable_cleaning:
            self.add_processor(DataCleaner())
        
        if self.config.enable_transformation:
            self.add_processor(DataTransformer())
        
        if self.config.enable_aggregation:
            self.add_processor(DataAggregator())
    
    def add_processor(self, processor: DataProcessor):
        """添加处理器"""
        self.processors.append(processor)
        logger.info(f"Added processor: {processor.get_name()}")
    
    def remove_processor(self, processor_name: str):
        """移除处理器"""
        self.processors = [p for p in self.processors if p.get_name() != processor_name]
        logger.info(f"Removed processor: {processor_name}")
    
    async def fetch_and_process(self, 
                               requests: List[DataRequest],
                               adapter_ids: Optional[List[str]] = None) -> PipelineResult:
        """获取并处理数据"""
        start_time = datetime.now()
        errors = []
        warnings = []
        
        try:
            # 并行获取数据
            if self.config.parallel_processing:
                data_responses = await self._fetch_data_parallel(requests, adapter_ids)
            else:
                data_responses = await self._fetch_data_sequential(requests, adapter_ids)
            
            # 合并数据
            combined_data = self._combine_data_responses(data_responses)
            
            if combined_data.empty:
                return PipelineResult(
                    success=False,
                    data=combined_data,
                    errors=["No data retrieved from any source"]
                )
            
            # 处理数据
            processed_data, processing_metadata = await self._process_data(combined_data)
            
            # 计算数据质量分数
            quality_score = self._calculate_quality_score(processed_data, processing_metadata)
            
            # 检查质量阈值
            if quality_score < self.config.quality_threshold:
                warnings.append(f"Data quality score {quality_score:.2f} below threshold {self.config.quality_threshold}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return PipelineResult(
                success=True,
                data=processed_data,
                metadata=processing_metadata,
                errors=errors,
                warnings=warnings,
                processing_time=processing_time,
                data_quality_score=quality_score,
                source_count=len(data_responses)
            )
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return PipelineResult(
                success=False,
                data=pd.DataFrame(),
                errors=[str(e)],
                processing_time=processing_time
            )
    
    async def _fetch_data_parallel(self, 
                                  requests: List[DataRequest],
                                  adapter_ids: Optional[List[str]] = None) -> List[DataResponse]:
        """并行获取数据"""
        tasks = []
        
        for i, request in enumerate(requests):
            adapter_id = adapter_ids[i] if adapter_ids and i < len(adapter_ids) else None
            task = global_data_source_registry.fetch_data(request, adapter_id)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Request {i} failed: {response}")
            elif isinstance(response, DataResponse):
                valid_responses.append(response)
        
        return valid_responses
    
    async def _fetch_data_sequential(self, 
                                    requests: List[DataRequest],
                                    adapter_ids: Optional[List[str]] = None) -> List[DataResponse]:
        """顺序获取数据"""
        responses = []
        
        for i, request in enumerate(requests):
            try:
                adapter_id = adapter_ids[i] if adapter_ids and i < len(adapter_ids) else None
                response = await global_data_source_registry.fetch_data(request, adapter_id)
                responses.append(response)
            except Exception as e:
                logger.error(f"Request {i} failed: {e}")
        
        return responses
    
    def _combine_data_responses(self, responses: List[DataResponse]) -> pd.DataFrame:
        """合并数据响应"""
        if not responses:
            return pd.DataFrame()
        
        dataframes = []
        
        for response in responses:
            if response.success and response.data_points:
                # 转换为DataFrame
                data_dict = {
                    'symbol': [dp.symbol for dp in response.data_points],
                    'timestamp': [dp.timestamp for dp in response.data_points],
                    'value': [dp.value for dp in response.data_points],
                    'volume': [dp.volume for dp in response.data_points]
                }
                
                # 添加元数据列
                for dp in response.data_points:
                    for key, value in dp.metadata.items():
                        if key not in data_dict:
                            data_dict[key] = []
                        data_dict[key].append(value)
                
                # 补齐列长度
                max_len = max(len(v) for v in data_dict.values())
                for key, values in data_dict.items():
                    while len(values) < max_len:
                        values.append(None)
                
                df = pd.DataFrame(data_dict)
                dataframes.append(df)
        
        if dataframes:
            return pd.concat(dataframes, ignore_index=True)
        else:
            return pd.DataFrame()
    
    async def _process_data(self, data: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """处理数据通过所有处理器"""
        current_data = data.copy()
        metadata = {
            'original_shape': data.shape,
            'processing_steps': []
        }
        
        for processor in self.processors:
            try:
                logger.info(f"Applying processor: {processor.get_name()}")
                current_data = await processor.process(current_data, metadata)
                metadata['processing_steps'].append(processor.get_name())
            except Exception as e:
                logger.error(f"Processor {processor.get_name()} failed: {e}")
                metadata['processing_errors'] = metadata.get('processing_errors', [])
                metadata['processing_errors'].append(f"{processor.get_name()}: {str(e)}")
        
        metadata['final_shape'] = current_data.shape
        return current_data, metadata
    
    def _calculate_quality_score(self, data: pd.DataFrame, metadata: Dict[str, Any]) -> float:
        """计算数据质量分数"""
        if data.empty:
            return 0.0
        
        score = 1.0
        
        # 检查空值比例
        null_ratio = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        score -= null_ratio * 0.3
        
        # 检查重复值比例
        if len(data) > 1:
            duplicate_ratio = data.duplicated().sum() / len(data)
            score -= duplicate_ratio * 0.2
        
        # 检查处理步骤完成情况
        expected_steps = len(self.processors)
        completed_steps = len(metadata.get('processing_steps', []))
        if expected_steps > 0:
            step_completion = completed_steps / expected_steps
            score *= step_completion
        
        # 检查错误
        error_count = len(metadata.get('processing_errors', []))
        if error_count > 0:
            score -= error_count * 0.1
        
        return max(0.0, min(1.0, score))


# 全局管道实例
global_data_pipeline = DataPipeline()


# 便捷函数
async def process_data_request(request: DataRequest, 
                              adapter_id: Optional[str] = None,
                              config: Optional[PipelineConfig] = None) -> PipelineResult:
    """处理单个数据请求的便捷函数"""
    pipeline = DataPipeline(config) if config else global_data_pipeline
    return await pipeline.fetch_and_process([request], [adapter_id] if adapter_id else None)


async def process_multi_source_data(requests: List[DataRequest],
                                   adapter_ids: Optional[List[str]] = None,
                                   config: Optional[PipelineConfig] = None) -> PipelineResult:
    """处理多源数据的便捷函数"""
    pipeline = DataPipeline(config) if config else global_data_pipeline
    return await pipeline.fetch_and_process(requests, adapter_ids)