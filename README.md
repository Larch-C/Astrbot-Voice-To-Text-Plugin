# AstrBot 语音转文字智能回复插件

## 该插件在Windows环境下对silk格式音频的转换依赖 [silk-v3-decoder](https://github.com/kn007/silk-v3-decoder) 开源项目。

https://github.com/kn007/silk-v3-decoder

## Windwos环境下该插件需要调用

##  [silk-v3-decoder/windows/silk2mp3.exe at master · kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder/blob/master/windows/silk2mp3.exe) 

## 该程序进行音频转换 但是目前该程序的<u>***安全性未知***</u>，如有用户有Windows环境下安装本插件的需求

## 请**<u>*自行甄别 silk-v3-decoder.exe 该程序是否安全*</u>**

一个AstrBot插件，支持多种音频格式的语音识别，并能够自动生成符合框架人格的智能回复。

## 使用本插件强烈建议配合 TTS 插件 https://github.com/muyouzhi6/astrabot_plugin_tts_emotion_router 使用 可实现按bot回复情绪使用不同的音色和语速进行全语音对话
# 注意注意！特别注意！不管你的怎么部署的astrbot框架，docker容器也好，直接丢服务器上的也好，都要能访问到 ffmpeg 指令，如何安装配置 ffmpeg 请往下看！插件里写了各个系统环境常用的 ffmpeg 路径，不一定有你所安装的路径！所以说一定要看清楚！

## 📁 架构组织结构

```
Astrbot-Voice-To-Text-Plugin-main/
├── main.py                            # 插件主入口文件
├── config.py                          # 统一配置管理
├── exceptions.py                      # 自定义异常体系
├── requirements.txt                   # 依赖声明文件
├── metadata.yaml                      # 插件元数据
├── _conf_schema.json                  # 配置模式定义
├── IMPORT_FIXES_GUIDE.md             # 导入问题解决方案指南
├── utils/                            # 工具层
│   ├── __init__.py                   # 包初始化
│   └── decorators.py                 # 装饰器工具集
├── core/                             # 核心组件层
│   ├── __init__.py                   # 核心模块导出（优化导入顺序）
│   ├── factory.py                    # 🆕 工厂模式组件管理
│   ├── temp_file_manager.py          # 临时文件统一管理
│   ├── audio_format_detector.py      # 音频格式检测器
│   ├── ffmpeg_manager.py             # FFmpeg管理器(缓存优化)
│   ├── conversion_strategies.py      # 转换策略模式实现
│   └── audio_converter.py            # 重构后的音频转换器（延迟导入）
└── services/                         # 业务服务层
    ├── __init__.py                   # 服务层包初始化
    ├── voice_processing_service.py   # 语音处理服务（工厂模式）
    ├── permission_service.py         # 权限检查服务
    └── stt_service.py                # STT调用服务
```

## 🚀 核心亮点

### 1. **🏗️ 架构优化**
- ✅ **单一职责原则**: 每个类专注单一功能
- ✅ **服务层解耦**: 业务逻辑与框架解耦
- ✅ **依赖注入**: 组件间低耦合设计
- ✅ **策略模式**: 音频转换策略可插拔
- 🆕 **工厂模式**: 统一组件创建，解决循环导入

### 2. **⚡ 性能优化**
- ✅ **FFmpeg路径缓存**: 避免重复搜索
- ✅ **异步文件操作**: 提升I/O性能
- ✅ **临时文件统一管理**: 自动清理机制
- ✅ **权限检查缓存**: 减少重复计算
- ✅ **重试机制**: 指数退避重试策略
- 🆕 **组件按需初始化**: 提升启动性能

### 3. **💎 代码优雅度**
- ✅ **统一异常处理**: 专用异常体系
- ✅ **装饰器消除重复**: 统一日志和性能监控
- ✅ **配置集中管理**: 消除硬编码
- ✅ **方法拆分重构**: 提升可读性
- ✅ **类型注解完善**: 提升代码可读性
- 🆕 **导入顺序优化**: 按依赖层次组织模块导入

### 4. **🔧 稳定性改进**
- 🆕 **循环导入修复**: 使用延迟导入和工厂模式彻底解决
- 🆕 **模块加载优化**: 重新组织 `__init__.py` 导入顺序
- 🆕 **组件依赖管理**: 统一的工厂类管理所有核心组件
- 🆕 **AstrBot兼容性**: 完美适配框架的动态插件加载机制

## ✨ 核心特性

### 🎤 强大的语音处理能力
- **多格式支持**: AMR、SILK、MP3、WAV、OGG、FLAC、M4A等主流音频格式
- **智能格式转换**: 自动检测并转换不支持的音频格式为STT兼容格式
- **多重转换策略**: PyDub、FFmpeg、备用方法等多种转换方案，确保最高成功率
- **文件验证**: 完整的文件完整性检查和格式验证机制

### 🧠 智能回复系统
- **框架人格集成**: 完全使用AstrBot框架配置的人格系统，确保回复风格一致
- **上下文感知**: 自动继承对话历史和上下文信息
- **自然语言处理**: 基于语音内容生成自然、贴切的AI回复

### 🔄 健壮的文件获取机制
- **10种备用方法**: 包含官方API、Base64转换、文件服务、URL下载等多种获取方式
- **智能路径搜索**: 自动在AstrBot数据目录、临时目录、系统目录中搜索语音文件
- **模式匹配**: 支持文件名模式匹配和glob搜索

### 🌐 全平台兼容
- **多平台支持**: 完美适配QQ、微信、Telegram等主流聊天平台
- **统一接口**: 使用AstrBot统一的消息处理接口，确保跨平台一致性

## 🏗️ 技术架构

### 核心组件
1. **VoiceToTextPlugin**: 主插件类，负责消息监听和流程控制
2. **AudioConverter**: 音频格式转换工具类，支持PyDub、FFmpeg等多种转换方案
3. **VoiceFileResolver**: 语音文件路径解析器，提供10种备用文件获取策略
4. **群聊权限管理**: 支持白名单/黑名单的精细化权限控制
5. **STT集成**: 直接调用AstrBot框架的STT提供商
6. **LLM集成**: 使用框架的人格系统进行智能回复

### 架构设计原则
- **模块化设计**: 各组件职责单一，低耦合高内聚
- **DRY原则**: 消除代码重复，统一封装文件解析逻辑
- **容错机制**: 多重备用方案，确保系统稳定性
- **异步处理**: 全异步架构，提升并发处理能力

### 处理流程
```
语音消息接收 → 文件路径获取 → 文件验证 → 格式检测 → 
格式转换(如需要) → STT语音识别 → 显示识别结果 → 
LLM智能回复 → 临时文件清理
```

## 📋 系统要求

### 基础环境
- **Python**: 3.8+ (推荐3.9+)
- **AstrBot**: 3.4.0+ (经过3.5.20+版本测试)
- **操作系统**: Windows/Linux/macOS

### 必要依赖
- `aiohttp`: 异步HTTP客户端，用于下载语音文件
- `pydub`: 音频处理库，用于音频格式转换
- `certifi`: SSL证书验证，确保HTTPS连接安全
- `pilk`: SILK格式解码库，作为FFmpeg的备用方案
- ~~`ffmpeg-python`~~: ~~FFmpeg Python接口~~ (代码中直接调用FFmpeg可执行文件，无需此库)
- ~~`silk-python`~~: ~~SILK格式支持~~ (已废弃，现使用FFmpeg+pilk处理SILK格式)

### 系统工具依赖

#### FFmpeg (必需)
FFmpeg是插件进行音频格式转换的核心依赖，必须正确安装才能保证插件正常工作。

##### Windows系统安装
**方法一：使用Chocolatey (推荐)**
```powershell
# 安装Chocolatey包管理器 (如果尚未安装)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装FFmpeg
choco install ffmpeg
```

**方法二：手动安装**
1. 访问 [FFmpeg官网](https://ffmpeg.org/download.html#build-windows)
2. 下载Windows预编译版本 (推荐essentials版本)
3. 解压到 `C:\ffmpeg` 目录
4. 将 `C:\ffmpeg\bin` 添加到系统PATH环境变量：
   - 右键"此电脑" → "属性" → "高级系统设置"
   - 点击"环境变量" → 在"系统变量"中找到"Path"
   - 点击"编辑" → "新建" → 输入 `C:\ffmpeg\bin`
   - 确定保存
5. 重启命令提示符，验证安装：
   ```cmd
   ffmpeg -version
   ```

**方法三：使用Scoop**
```powershell
# 安装Scoop (如果尚未安装)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# 安装FFmpeg
scoop install ffmpeg
```

##### Linux系统安装
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL/Fedora:**
```bash
# CentOS/RHEL (需要EPEL源)
sudo yum install epel-release
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

##### macOS系统安装
**使用Homebrew (推荐):**
```bash
# 安装Homebrew (如果尚未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装FFmpeg
brew install ffmpeg
```

**使用MacPorts:**
```bash
sudo port install ffmpeg
```

##### 容器环境安装

**Docker容器内安装:**
```dockerfile
# 在Dockerfile中添加
RUN apt-get update && apt-get install -y ffmpeg

# 或者对于Alpine Linux
RUN apk add --no-cache ffmpeg
```

**Docker Compose示例:**
```yaml
version: '3.8'
services:
  astrbot:
    image: python:3.9-slim
    volumes:
      - ./:/app
    working_dir: /app
    command: |
      bash -c "
        apt-get update && 
        apt-get install -y ffmpeg && 
        pip install -r requirements.txt && 
        python main.py
      "
```

##### 验证安装
安装完成后，在终端/命令提示符中运行以下命令验证：
```bash
ffmpeg -version
```
应该能看到FFmpeg的版本信息。

##### 常见问题解决

**Windows PATH问题:**
如果提示"ffmpeg不是内部或外部命令"：
1. 确认FFmpeg已下载并解压
2. 检查PATH环境变量是否正确添加
3. 重启命令提示符或重启计算机
4. 使用绝对路径测试：`C:\ffmpeg\bin\ffmpeg.exe -version`

**权限问题 (Linux/macOS):**
```bash
# 确保FFmpeg有执行权限
chmod +x /usr/local/bin/ffmpeg
```

**网络问题:**
如果下载失败，可以使用国内镜像源或手动下载安装包。

## 🚀 安装和配置

### 1. 插件安装
```bash
# 将插件文件夹放入AstrBot的packages目录
cp -r VoiceToTextPlugin_by_nickmo/ /path/to/astrbot/packages/
```

### 2. 依赖安装
```bash
# 进入插件目录
cd packages/VoiceToTextPlugin_by_nickmo/

# 安装Python依赖
pip install -r requirements.txt

# 或者手动安装核心依赖
pip install aiohttp>=3.8.0 pydub>=0.25.1 certifi>=2021.10.8 pilk>=0.2.3
```

**依赖说明**:
- **aiohttp**: 用于异步下载语音文件，支持HTTPS和代理
- **pydub**: 核心音频处理库，支持多种格式转换
- **certifi**: 提供SSL证书包，确保HTTPS连接安全性
- **pilk**: SILK格式专用解码库，处理QQ语音等特殊格式

### 3. STT服务配置选择

插件现在支持两种STT服务来源：

#### 🔧 方式一：使用AstrBot框架STT (推荐)
- 在AstrBot管理面板中配置STT服务提供商
- 插件配置中选择 `STT_Source` 为 `framework`
- 无需额外配置，直接使用框架统一管理的STT服务

#### 🔌 方式二：使用插件独立STT API
- 插件配置中选择 `STT_Source` 为 `plugin`
- 支持10+主流STT提供商，每个都有专门优化的API格式

### 4. 插件配置

#### 基础配置
```json
{
  "Voice_Recognition": {
    "STT_Source": "framework",           // STT服务来源: framework 或 plugin
    "Enable_Voice_Processing": true,     // 是否启用语音消息处理
    "Max_Audio_Size_MB": 25             // 文件大小限制(MB)
  },
  "Chat_Reply": {
    "Enable_Chat_Reply": true,          // 启用智能回复
    "Use_Framework_Personality": true   // 使用框架人格系统
  },
  "Output_Settings": {
    "Console_Output": true,             // 控制台输出识别结果
    "Show_Recognition_Result": true     // 向用户显示识别结果
  }
}
```

#### STT提供商配置（仅当STT_Source为plugin时显示）

##### 🚀 高速推理服务
**Groq - 超快Whisper推理**
```json
{
  "STT_API_Config": {
    "Provider_Type": "groq",
    "API_Key": "gsk_your-groq-api-key",
    "Model": "whisper-large-v3"
  }
}
```

**OpenAI Whisper - 官方服务**
```json
{
  "STT_API_Config": {
    "Provider_Type": "openai", 
    "API_Key": "sk-your-openai-api-key",
    "Model": "whisper-1"
  }
}
```

##### 🇨🇳 国内优化服务
**SiliconFlow - 硅基流动**
```json
{
  "STT_API_Config": {
    "Provider_Type": "siliconflow",
    "API_Key": "sk-your-siliconflow-key",
    "Model": "FunAudioLLM/SenseVoiceSmall"
  }
}
```

**MiniMax - 海螺AI**
```json
{
  "STT_API_Config": {
    "Provider_Type": "minimax",
    "API_Key": "your-minimax-key",
    "Model": "speech-01"
  }
}
```

##### 🏢 企业级服务
**Deepgram - 专业语音识别**
```json
{
  "STT_API_Config": {
    "Provider_Type": "deepgram",
    "API_Key": "your-deepgram-key",
    "Model": "nova-2"
  }
}
```

**Azure Speech Services**
```json
{
  "STT_API_Config": {
    "Provider_Type": "azure",
    "API_Key": "your-azure-key",
    "Model": "whisper"
  }
}
```

##### 📱 移动社交优化
**VolcEngine - 火山引擎**、**Tencent - 腾讯云**、**Baidu - 百度智能云** 等国内服务商同样支持

##### 🔧 自定义服务
```json
{
  "STT_API_Config": {
    "Provider_Type": "custom",
    "API_Key": "your-custom-key",
    "API_Base_URL": "https://your-api.example.com/v1",
    "Model": "your-model-name"
  }
}
```

##### 🔥 完全自定义STT服务提供商 (other类型)

当现有的STT提供商都无法满足需求时，可以使用"other"类型来对接任意第三方STT API。此功能提供完全的自定义能力，支持任意API格式。

**基本配置示例:**
```json
{
  "STT_API_Config": {
    "Provider_Type": "other",
    "API_Key": "your-custom-api-key",
    "API_Base_URL": "https://your-stt-api.example.com",
    "Model": "your-model-name",
    "Custom_Endpoint": "/v1/audio/transcribe",
    "Custom_Request_Method": "POST",
    "Custom_Content_Type": "multipart/form-data",
    "Custom_Response_Path": "result.text",
    "Custom_Request_Body": {
      "model": "{model}",
      "language": "zh-CN"
    },
    "Custom_Headers": {
      "X-API-Version": "v1.0",
      "User-Agent": "AstrBot-Plugin"
    }
  }
}
```

**详细参数说明:**

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `Provider_Type` | string | ✅ | 固定值 "other" | `"other"` |
| `API_Key` | string | ✅ | API认证密钥 | `"sk-1234567890abcdef"` |
| `API_Base_URL` | string | ✅ | API服务器基础URL | `"https://api.example.com"` |
| `Model` | string | ✅ | 语音识别模型名称 | `"whisper-v3"` |
| `Custom_Endpoint` | string | ✅ | API端点路径 | `"/v1/audio/transcriptions"` |
| `Custom_Request_Method` | string | ✅ | HTTP请求方法 | `"POST"` / `"PUT"` / `"PATCH"` |
| `Custom_Content_Type` | string | ✅ | 请求内容类型 | 见下方详细说明 |
| `Custom_Response_Path` | string | ✅ | 响应文本提取路径 | `"text"` / `"data.transcript"` |
| `Custom_Request_Body` | object | ⭕ | 自定义请求体字段 | 见下方示例 |
| `Custom_Headers` | object | ⭕ | 自定义请求头 | 见下方示例 |

**支持的内容类型 (Custom_Content_Type):**

1. **multipart/form-data** - 表单上传（推荐）
   - 适用于大多数STT API
   - 自动处理文件上传和表单字段

2. **application/json** - JSON格式
   - 音频数据会自动转换为base64编码
   - 适用于REST风格的API

3. **application/octet-stream** - 二进制流
   - 直接发送音频二进制数据
   - 适用于简单的二进制API

**响应路径提取 (Custom_Response_Path) 示例:**

```javascript
// 如果API返回:
{
  "status": "success",
  "data": {
    "transcript": "你好，世界！",
    "confidence": 0.98
  }
}
// 设置 Custom_Response_Path 为: "data.transcript"

// 如果API返回:
{
  "result": "语音识别结果文本"
}
// 设置 Custom_Response_Path 为: "result"

// 如果API返回:
{
  "transcription": {
    "results": [
      {
        "text": "识别的文本内容"
      }
    ]
  }
}
// 设置 Custom_Response_Path 为: "transcription.results.0.text"
```

**变量替换支持:**

在 `Custom_Request_Body` 中可以使用以下变量：

- `{api_key}` - 替换为配置的API密钥
- `{model}` - 替换为配置的模型名称  
- `{audio_base64}` - 替换为base64编码的音频数据（仅JSON格式）

**完整配置示例集合:**

**示例1: 类似OpenAI格式的API**
```json
{
  "STT_API_Config": {
    "Provider_Type": "other",
    "API_Key": "sk-custom123456",
    "API_Base_URL": "https://stt-api.company.com",
    "Model": "whisper-large",
    "Custom_Endpoint": "/v1/audio/transcriptions",
    "Custom_Request_Method": "POST",
    "Custom_Content_Type": "multipart/form-data",
    "Custom_Response_Path": "text",
    "Custom_Request_Body": {
      "model": "{model}",
      "response_format": "json",
      "language": "zh"
    },
    "Custom_Headers": {
      "Authorization": "Bearer {api_key}"
    }
  }
}
```

**示例2: JSON格式的企业内部API**
```json
{
  "STT_API_Config": {
    "Provider_Type": "other", 
    "API_Key": "internal-api-token-xyz",
    "API_Base_URL": "https://internal-stt.corp.com",
    "Model": "corporate-v2.1",
    "Custom_Endpoint": "/api/speech/recognize",
    "Custom_Request_Method": "POST",
    "Custom_Content_Type": "application/json",
    "Custom_Response_Path": "data.recognition.transcript",
    "Custom_Request_Body": {
      "audio_data": "{audio_base64}",
      "model_version": "{model}",
      "options": {
        "language": "zh-CN",
        "enable_punctuation": true,
        "sample_rate": 16000
      }
    },
    "Custom_Headers": {
      "X-Auth-Token": "{api_key}",
      "Content-Type": "application/json",
      "X-Client-Version": "astrbot-plugin-v1.0"
    }
  }
}
```

**示例3: 简单的二进制流API**
```json
{
  "STT_API_Config": {
    "Provider_Type": "other",
    "API_Key": "binary-api-key-789",
    "API_Base_URL": "https://simple-stt.service.io",
    "Model": "default",
    "Custom_Endpoint": "/transcribe",
    "Custom_Request_Method": "POST", 
    "Custom_Content_Type": "application/octet-stream",
    "Custom_Response_Path": "transcript",
    "Custom_Headers": {
      "X-API-Key": "{api_key}",
      "Accept": "application/json"
    }
  }
}
```

**调试和测试建议:**

1. **逐步验证**: 先用简单的配置测试连通性
2. **查看日志**: 使用 `/voice_debug` 命令查看详细请求信息
3. **响应格式**: 先确认API的响应JSON结构，再配置提取路径
4. **认证方式**: 不同API的认证方法可能不同，灵活使用Custom_Headers

**常见问题解决:**

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 401 Unauthorized | API密钥错误或认证方式不对 | 检查API_Key和Custom_Headers中的认证配置 |
| 400 Bad Request | 请求格式不符合API要求 | 检查Custom_Request_Body和Content_Type设置 |
| 提取文本失败 | 响应路径配置错误 | 检查Custom_Response_Path，确保路径正确 |
| 连接超时 | API服务器响应慢或不可达 | 检查API_Base_URL和网络连接 |

通过"other"类型的完全自定义配置，您可以对接任何STT服务提供商，实现真正的万能语音识别接口！

## 📚 配置选项详解

### 语音识别设置
- **Enable_Voice_Processing**: 是否启用语音消息处理
- **Max_Audio_Size_MB**: 语音文件大小限制(默认25MB)

### 智能回复设置
- **Enable_Chat_Reply**: 是否启用智能回复功能
- **Use_Framework_Personality**: 使用AstrBot框架人格系统(推荐)

### 输出设置
- **Console_Output**: 是否在控制台输出识别结果
- **Show_Recognition_Result**: 是否向用户显示识别结果
- **Result_Format**: 识别结果显示格式

### 处理配置
- **Processing_Timeout**: 语音处理超时时间(秒)
- **Retry_Count**: 识别失败重试次数
- **Enable_Error_Notification**: 是否启用错误通知

## 🎯 使用方法

### 基本使用
1. 确保AstrBot已配置STT和LLM提供商
2. 启用本插件
3. 直接发送语音消息即可自动处理

### 管理命令
- `/voice_status`: 查看插件状态和配置信息
- `/voice_test`: 测试STT和LLM提供商连接状态
- `/voice_providers`: 查看所有支持的STT提供商详细信息
- `/voice_debug`: 调试群聊权限配置

### 支持的音频格式
- **原生支持**: MP3, WAV, FLAC, M4A, OGG
- **转换支持**: AMR, SILK(QQ语音), MP4音频等
- **自动检测**: 基于文件头智能识别格式

## 🔧 框架集成

### 核心架构设计
插件采用模块化设计，主要由以下组件构成：

- **VoiceToTextPlugin**: 主插件类，集成AstrBot事件处理
- **AudioConverter**: 音频转换工具类，支持多格式处理
- **VoiceFileResolver**: 语音文件解析器，10种获取策略

### STT集成
```python
# 直接调用AstrBot框架STT提供商
stt_provider = self.context.get_using_stt_provider()
result = await stt_provider.get_text(audio_file_path)
```

### LLM集成
```python
# 使用框架人格系统生成回复
yield event.request_llm(
    prompt=f"用户通过语音说了: {text}\n请自然地回应用户的语音内容。",
    session_id=curr_cid,
    contexts=context,
    conversation=conversation
)
```

### 音频处理流程
```python
# 1. 文件获取 - 使用VoiceFileResolver
original_file_path = await self.voice_file_resolver.resolve_voice_file_path(voice)

# 2. 格式检测与转换
audio_format = self.audio_converter.detect_audio_format(original_file_path)
if needs_conversion:
    converted_path = await self.convert_audio_file_with_retry(original_file_path)

# 3. 语音识别
transcribed_text = await self.call_official_stt(final_file_path)

# 4. 智能回复 (可选)
if self.enable_chat_reply and self.should_generate_reply(event):
    async for reply in self.call_official_chatllm(event, transcribed_text):
        yield reply
```

### 人格系统
- 插件完全依赖AstrBot框架的人格配置
- 支持动态人格切换(`/persona`命令)
- 自动继承对话历史和上下文
- 确保语音回复与文本回复风格一致

## 🛠️ 技术实现详解

### 音频格式检测
```python
def detect_audio_format(self, file_path: str) -> str:
    # 读取文件头进行格式识别
    # 支持AMR、SILK、MP3、WAV、OGG等格式
    # 基于二进制特征码精确识别
```

### 多重转换策略
1. **PyDub转换**: 处理标准音频格式
2. **FFmpeg转换**: 处理复杂编码格式
3. **备用转换**: 尝试原始数据转换

### 文件获取机制
1. 官方API方法
2. Base64数据转换
3. 文件服务注册
4. 直接路径访问
5. URL资源下载
6. 多种搜索策略

## 🔍 故障排除

### 常见问题

#### 1. 语音识别失败
**可能原因**:
- STT提供商未配置或配置错误
- 音频文件格式不支持
- 网络连接问题
- API配额不足

**解决方案**:
```bash
# 检查STT提供商状态
/voice_status

# 查看详细日志
tail -f astrbot.log | grep "voice"

# 测试提供商连接
/voice_test
```

#### 2. 音频转换失败
**可能原因**:
- FFmpeg未安装或不在PATH中
- 音频文件损坏
- 临时目录权限不足
- 磁盘空间不足

**解决方案**:
```bash
# 检查FFmpeg安装
ffmpeg -version

# 检查临时目录权限
ls -la /tmp

# 检查磁盘空间
df -h
```

#### 3. 智能回复无响应
**可能原因**:
- LLM提供商未配置
- API密钥无效
- 网络连接问题
- 人格配置错误

**解决方案**:
- 检查AstrBot LLM提供商配置
- 验证API密钥有效性
- 检查网络连接状态
- 确认人格配置正确

### 日志分析
插件提供详细的分级日志：

```bash
# 查看插件相关日志
grep "voice_to_text\|VoiceToText" astrbot.log

# 查看错误日志
grep "ERROR.*voice" astrbot.log

# 查看转换日志
grep "转换\|convert" astrbot.log
```

### 性能优化
- 调整`max_audio_size_mb`限制大文件
- 启用`enable_audio_conversion`提高兼容性
- 合理设置`retry_count`平衡成功率和响应速度

## 📊 性能特性

### 处理能力
- **并发处理**: 支持多用户同时语音识别
- **内存管理**: 自动清理临时文件，避免内存泄漏
- **错误恢复**: 多重备用方案，确保高成功率

### 可靠性
- **重试机制**: 转换和识别失败自动重试
- **错误隔离**: 单个错误不影响其他用户
- **优雅降级**: 部分功能失败不影响核心功能

## 🔄 更新日志

### v1.0.0 (当前版本)
#### 🆕 新增功能
- 完整的语音转文字功能
- 集成AstrBot框架人格系统
- 多种音频格式支持和转换
- 10种文件获取备用方案
- 完善的错误处理和重试机制
- Web配置界面支持

#### 🔧 技术改进
- 修复STT接口调用错误(`get_text`方法)
- 优化音频转换策略
- 增强文件验证机制
- 改进日志输出和错误提示

#### 🎯 兼容性
- 支持AstrBot 3.4.0+
- 兼容多种STT和LLM提供商
- 跨平台支持(Windows/Linux/macOS)

## 📝 开发者信息

### 作者
- **开发者**: NickMo
- **版本**: 1.0.0
- **许可证**: MIT License

### 技术栈
- **主要语言**: Python 3.8+
- **框架**: AstrBot Plugin API
- **音频处理**: PyDub + FFmpeg
- **异步处理**: asyncio + aiohttp
- **配置管理**: JSON Schema

### 贡献指南
欢迎提交Issue和Pull Request来改进插件：

1. **Bug报告**: 请提供详细的错误信息和复现步骤
2. **功能建议**: 描述需求和使用场景
3. **代码贡献**: 遵循项目代码规范，添加必要的测试

### 技术支持
如果遇到问题：

1. 查看AstrBot日志获取详细错误信息
2. 使用`/voice_status`和`/voice_test`命令检查状态
3. 在GitHub Issues中搜索相似问题
4. 提交新Issue并附上相关日志和环境信息

***

## ⚠️ 重要提示

### 使用前确认
- ✅ AstrBot已正确安装并运行
- ✅ STT提供商已配置且可用
- ✅ LLM提供商已配置且可用
- ✅ 必要的系统依赖已安装

### 最佳实践
- 🔧 定期检查插件状态(`/voice_status`)
- 📊 监控日志输出发现潜在问题
- 🎯 根据使用情况调整配置参数
- 🔄 保持AstrBot和插件版本更新

**开始使用语音转文字功能，享受更智能的聊天体验！** 🚀

## 故障排除

### 常见问题

1. **语音识别失败**
   - 检查AstrBot是否配置了STT服务提供商
   - 确认语音文件格式是否支持
   - 查看插件日志获取详细错误信息

2. **音频转换失败**
   - 确认FFmpeg是否正确安装
   - 检查临时目录是否有写入权限
   - 确认音频文件是否损坏

3. **智能回复无响应**
   - 检查AstrBot是否配置了ChatLLM提供商
   - 确认API密钥是否有效
   - 查看网络连接状态

### 日志查看

插件会在AstrBot日志中输出详细的处理信息

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多格式语音识别
- 集成智能回复功能
- 添加Web配置界面

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个插件。

## 支持

如果遇到问题，请：

1. 查看AstrBot日志获取详细错误信息
2. 在GitHub Issues中搜索相似问题
3. 提交新的Issue并附上相关日志

***

**注意**: 使用前请确保已正确配置AstrBot的STT和ChatLLM服务提供商。

