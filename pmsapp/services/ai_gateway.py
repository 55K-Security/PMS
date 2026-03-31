"""
AI网关服务 - 统一管理多种AI服务提供商
支持 OpenAI/Claude兼容API 和 私有化部署模型
"""

import json
import logging
import requests
import base64
import time
from typing import List, Dict, Any, Optional, Generator
from django.conf import settings
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class KeyManager:
    """密钥管理器 - 使用PBKDF2派生密钥"""
    
    SALT = b'pms_ai_config_salt_v1'
    ITERATIONS = 100000
    
    @classmethod
    def derive_key(cls, secret_key: str = None) -> bytes:
        """使用PBKDF2派生加密密钥"""
        if secret_key is None:
            secret_key = settings.SECRET_KEY
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=cls.SALT,
            iterations=cls.ITERATIONS,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    
    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """加密API密钥"""
        key = cls.derive_key()
        cipher = Fernet(key)
        return cipher.encrypt(plaintext.encode()).decode()
    
    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """解密API密钥"""
        key = cls.derive_key()
        cipher = Fernet(key)
        return cipher.decrypt(ciphertext.encode()).decode()


class RateLimiter:
    """请求频率限制器"""
    
    _cache: Dict[str, List[float]] = {}
    _limits = {
        'chat': (20, 60),      # 20次/分钟
        'config': (10, 60),     # 10次/分钟
        'report': (5, 300),     # 5次/5分钟
    }
    
    @classmethod
    def check(cls, key: str, action: str) -> bool:
        """检查是否超过频率限制"""
        now = time.time()
        limit, window = cls._limits.get(action, (60, 60))
        
        if key not in cls._cache:
            cls._cache[key] = []
        
        cls._cache[key] = [t for t in cls._cache[key] if now - t < window]
        
        if len(cls._cache[key]) >= limit:
            return False
        
        cls._cache[key].append(now)
        return True


class AIGateway:
    """AI服务网关，统一管理多种AI服务提供商"""
    
    SUPPORTED_PROVIDERS = ['openai', 'claude', 'private']
    
    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {}
        self._load_configs()
    
    def _load_configs(self):
        """从数据库加载AI配置"""
        try:
            from pmsapp.models import SystemSettings
            configs = SystemSettings.objects.filter(setting_type='ai', is_enabled=True)
            for config in configs:
                self.providers[config.setting_key] = {
                    'provider': config.setting_value,
                    'config': json.loads(config.description) if config.description else {}
                }
        except Exception as e:
            logger.warning(f"加载AI配置失败: {e}")
    
    def chat(self, provider: str, messages: List[dict], stream: bool = True, **kwargs) -> Any:
        """
        发送对话请求
        
        Args:
            provider: 服务提供商标识 ("openai", "claude", "private")
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            stream: 是否使用流式响应
            **kwargs: 其他参数如 temperature, max_tokens 等
            
        Returns:
            字符串响应或生成器
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError("不支持的AI服务提供商")
        
        user_key = kwargs.get('user_id', 'anonymous')
        if not RateLimiter.check(user_key, 'chat'):
            raise RuntimeError("请求过于频繁，请稍后再试")
        
        if provider == 'openai':
            return self._chat_openai(messages, stream, **kwargs)
        elif provider == 'claude':
            return self._chat_claude(messages, stream, **kwargs)
        elif provider == 'private':
            return self._chat_private(messages, stream, **kwargs)
    
    def _chat_openai(self, messages: List[dict], stream: bool = True, **kwargs) -> Any:
        """OpenAI API对接"""
        config = self._get_provider_config('openai')
        if not config:
            raise RuntimeError("OpenAI配置未找到，请先配置AI服务")
        
        api_url = config.get('api_url', 'https://api.openai.com/v1/chat/completions')
        api_key = config.get('api_key')
        model = config.get('model_name', 'gpt-3.5-turbo')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': model,
            'messages': messages,
            'stream': stream,
        }
        
        if 'temperature' in kwargs:
            payload['temperature'] = kwargs['temperature']
        if 'max_tokens' in kwargs:
            payload['max_tokens'] = kwargs['max_tokens']
        
        try:
            if stream:
                return self._stream_request(api_url, headers, payload)
            else:
                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        except requests.exceptions.Timeout:
            raise TimeoutError("AI服务请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise RuntimeError(f"AI服务调用失败: {str(e)}")
    
    def _chat_claude(self, messages: List[dict], stream: bool = True, **kwargs) -> Any:
        """Claude API对接"""
        config = self._get_provider_config('claude')
        if not config:
            raise RuntimeError("Claude配置未找到，请先配置AI服务")
        
        api_url = config.get('api_url', 'https://api.anthropic.com/v1/messages')
        api_key = config.get('api_key')
        model = config.get('model_name', 'claude-3-sonnet-20240229')
        
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        }
        
        payload = {
            'model': model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', 1024),
        }
        
        if 'temperature' in kwargs:
            payload['temperature'] = kwargs['temperature']
        
        try:
            if stream:
                return self._stream_request(api_url, headers, payload)
            else:
                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                return response.json().get('content', [{}])[0].get('text', '')
        except requests.exceptions.Timeout:
            raise TimeoutError("AI服务请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API调用失败: {e}")
            raise RuntimeError(f"AI服务调用失败: {str(e)}")
    
    def _chat_private(self, messages: List[dict], stream: bool = True, **kwargs) -> Any:
        """私有化部署模型对接"""
        config = self._get_provider_config('private')
        if not config:
            raise RuntimeError("私有化部署配置未找到，请先配置AI服务")
        
        api_url = config.get('api_url')
        api_key = config.get('api_key', '')
        model = config.get('model_name', '')
        
        headers = {
            'Content-Type': 'application/json',
        }
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        payload = {
            'model': model,
            'messages': messages,
            'stream': stream,
        }
        
        if 'temperature' in kwargs:
            payload['temperature'] = kwargs['temperature']
        if 'max_tokens' in kwargs:
            payload['max_tokens'] = kwargs['max_tokens']
        
        try:
            if stream:
                return self._stream_request(api_url, headers, payload)
            else:
                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                if 'choices' in result:
                    return result['choices'][0]['message']['content']
                elif 'response' in result:
                    return result['response']
                return str(result)
        except requests.exceptions.Timeout:
            raise TimeoutError("AI服务请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"私有化模型API调用失败: {e}")
            raise RuntimeError(f"AI服务调用失败: {str(e)}")
    
    def _stream_request(self, url: str, headers: dict, payload: dict) -> Generator[str, None, None]:
        """流式请求处理"""
        payload['stream'] = True
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = line_text[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                            elif 'delta' in chunk:
                                yield chunk['delta'].get('content', '')
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"流式请求失败: {e}")
            raise RuntimeError(f"流式请求失败: {str(e)}")
    
    def _get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """获取指定提供商配置"""
        try:
            from pmsapp.models import SystemSettings
            config = SystemSettings.objects.filter(
                setting_type='ai',
                setting_key=provider,
                is_enabled=True
            ).first()
            
            if config and config.description:
                return json.loads(config.description)
            return None
        except Exception as e:
            logger.error(f"获取{provider}配置失败: {e}")
            return None
    
    def validate_config(self, config: dict) -> tuple:
        """
        验证AI配置有效性
        
        Args:
            config: 配置字典，包含 provider, api_url, api_key, model_name
            
        Returns:
            (是否通过, 错误信息)
        """
        provider = config.get('provider')
        api_url = config.get('api_url', '')
        api_key = config.get('api_key', '')
        model_name = config.get('model_name', '')
        
        if not provider:
            return False, "缺少provider参数"
        
        if provider not in self.SUPPORTED_PROVIDERS:
            return False, f"不支持的提供商: {provider}"
        
        if not api_url:
            return False, "缺少api_url参数"
        
        if not api_key:
            return False, "缺少api_key参数"
        
        if not model_name:
            return False, "缺少model_name参数"
        
        try:
            if provider == 'openai':
                test_url = f"{api_url.rstrip('/')}/v1/models"
                response = requests.get(test_url, headers={'Authorization': f'Bearer {api_key}'}, timeout=10)
                if response.status_code == 401:
                    return False, "API Key无效"
                elif response.status_code != 200:
                    return False, f"API请求失败: {response.status_code}"
            elif provider == 'claude':
                test_url = 'https://api.anthropic.com/v1/messages'
                response = requests.post(test_url, headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                }, json={
                    'model': model_name,
                    'messages': [{'role': 'user', 'content': 'test'}],
                    'max_tokens': 1
                }, timeout=10)
                if response.status_code == 401:
                    return False, "API Key无效"
                elif response.status_code != 200:
                    return False, f"API请求失败: {response.status_code}"
            else:
                response = requests.get(api_url, timeout=10)
                if response.status_code not in [200, 401, 403]:
                    return False, f"API请求失败: {response.status_code}"
            
            return True, "配置有效"
        except requests.exceptions.Timeout:
            return False, "连接超时，请检查API地址是否正确"
        except requests.exceptions.RequestException as e:
            return False, f"连接失败: {str(e)}"
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def save_config(self, provider: str, api_url: str, api_key: str, model_name: str, is_default: bool = True) -> bool:
        """
        保存AI配置
        
        Args:
            provider: 提供商类型
            api_url: API地址
            api_key: API密钥
            model_name: 模型名称
            is_default: 是否设为默认
            
        Returns:
            是否保存成功
        """
        try:
            from pmsapp.models import SystemSettings
            
            encrypted_key = KeyManager.encrypt(api_key)
            
            config_data = json.dumps({
                'api_url': api_url,
                'api_key': encrypted_key,
                'model_name': model_name,
            })
            
            if is_default:
                SystemSettings.objects.filter(setting_type='ai').update(is_enabled=False)
            
            SystemSettings.objects.update_or_create(
                setting_type='ai',
                setting_key=provider,
                defaults={
                    'setting_value': provider,
                    'description': config_data,
                    'is_enabled': is_default
                }
            )
            
            self._load_configs()
            return True
        except Exception as e:
            logger.error(f"保存AI配置失败")
            return False
    
    def get_config(self, provider: str = None) -> Optional[Dict[str, Any]]:
        """
        获取AI配置
        
        Args:
            provider: 提供商类型，不传则返回默认配置
            
        Returns:
            配置字典
        """
        try:
            from pmsapp.models import SystemSettings
            
            query = SystemSettings.objects.filter(setting_type='ai', is_enabled=True)
            if provider:
                query = query.filter(setting_key=provider)
            
            config = query.first()
            if not config or not config.description:
                return None
            
            config_data = json.loads(config.description)
            
            decrypted_key = KeyManager.decrypt(config_data['api_key'])
            config_data['api_key'] = decrypted_key
            
            return config_data
        except Exception as e:
            logger.error(f"获取AI配置失败")
            return None
