# -*- coding: utf-8 -*-
"""配置管理模块

负责读取和管理应用程序配置
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config: Dict[str, Any] = {}
        self.config_file_path: Optional[str] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        # 获取配置文件路径
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_file_path = os.path.join(project_root, 'config.yaml')
        
        # 默认配置
        default_config = {
            'environment': {
                'env_root_dir': './envs'
            },
            'service': {
                'port': 5001,
                'debug': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'python_envs.log'
            }
        }
        
        # 加载配置文件
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    logger.info(f"成功加载配置文件: {self.config_file_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
                self.config = default_config
        else:
            logger.warning(f"配置文件不存在: {self.config_file_path}，使用默认配置")
            self.config = default_config
        
        # 合并默认配置
        for key, value in default_config.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config[key]:
                        self.config[key][sub_key] = sub_value
    
    def get_env_root_dir(self) -> str:
        """获取虚拟环境根目录
        
        Returns:
            虚拟环境根目录的绝对路径
        """
        env_root_dir = self.config.get('environment', {}).get('env_root_dir', './envs')
        
        # 转换为绝对路径
        if not os.path.isabs(env_root_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            env_root_dir = os.path.join(project_root, env_root_dir)
        
        return os.path.abspath(env_root_dir)
    
    def get_service_port(self) -> int:
        """获取服务端口
        
        Returns:
            服务端口号
        """
        return self.config.get('service', {}).get('port', 5001)
    
    def is_debug_mode(self) -> bool:
        """获取调试模式设置
        
        Returns:
            是否启用调试模式
        """
        return self.config.get('service', {}).get('debug', True)
    
    def get_logging_level(self) -> str:
        """获取日志级别
        
        Returns:
            日志级别
        """
        return self.config.get('logging', {}).get('level', 'INFO')
    
    def get_logging_file(self) -> str:
        """获取日志文件路径
        
        Returns:
            日志文件路径
        """
        log_file = self.config.get('logging', {}).get('file', 'python_envs.log')
        
        # 转换为绝对路径
        if not os.path.isabs(log_file):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_file = os.path.join(project_root, log_file)
        
        return os.path.abspath(log_file)
    
    def reload_config(self) -> None:
        """重新加载配置文件"""
        self._load_config()

# 创建全局配置管理器实例
config_manager = ConfigManager()