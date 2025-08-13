# AstrBot 语音转文字智能回复插件

一个功能强大且高度集成的AstrBot插件，支持多种音频格式的语音识别，并能够自动生成符合框架人格的智能回复。

# 注意注意！特别注意！不管你的怎么部署的astrbot框架，docker容器也好，直接丢服务器上的也好，都要能访问到 ffmpeg 指令，如何安装配置 ffmpeg 请往下看！插件里写了各个系统环境常用的 ffmpeg 路径，不一定有你所安装的路径！所以说一定要看清楚！

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
2. **AudioConverter**: 音频格式转换工具类，支持多种转换方案
3. **语音文件获取系统**: 10种备用方法确保文件获取成功率
4. **STT集成**: 直接调用AstrBot框架的STT提供商
5. **LLM集成**: 使用框架的人格系统进行智能回复

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
- `aiohttp>=3.8.0`: 异步HTTP客户端
- `pydub>=0.25.1`: 音频处理库
- `ffmpeg-python>=0.2.0`: FFmpeg Python接口
- ~~`silk-python>=1.0.0`~~: ~~SILK格式支持~~ (已废弃，现使用FFmpeg处理SILK格式)

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

# 安装依赖
pip install -r requirements.txt
```

### 3. AstrBot配置
在AstrBot管理面板中配置：

#### STT服务提供商
- 支持 OpenAI Whisper API
- 支持 Groq (更快的Whisper推理)
- 支持 Deepgram (实时语音识别)
- 支持 Azure Speech Services
- 支持其他兼容 OpenAI 格式的语音转文字服务

#### ChatLLM提供商
- 配置任意支持的LLM提供商(OpenAI、Claude、Gemini等)
- 设置合适的人格配置

### 4. 插件配置
通过AstrBot Web界面配置插件参数：

#### 基础配置示例
```json
{
  "enable_chat_reply": true,        // 启用智能回复
  "console_output": true,           // 控制台输出识别结果
  "enable_audio_conversion": true,  // 启用音频格式转换
  "max_audio_size_mb": 25          // 文件大小限制(MB)
}
```

#### STT API 配置示例

**OpenAI Whisper 配置:**
```json
{
  "STT_API_Config": {
    "API_Key": "sk-your-openai-api-key",
    "API_Base_URL": "https://api.openai.com/v1",
    "Model": "whisper-1",
    "Provider_Type": "openai"
  }
}
```

**Groq 配置 (更快的 Whisper 推理):**
```json
{
  "STT_API_Config": {
    "API_Key": "gsk_your-groq-api-key",
    "API_Base_URL": "https://api.groq.com/openai/v1",
    "Model": "whisper-large-v3",
    "Provider_Type": "groq"
  }
}
```

**Deepgram 配置:**
```json
{
  "STT_API_Config": {
    "API_Key": "your-deepgram-api-key",
    "API_Base_URL": "https://api.deepgram.com/v1",
    "Model": "nova-2",
    "Provider_Type": "deepgram",
    "Custom_Headers": {
      "Content-Type": "audio/wav"
    }
  }
}
```

**Azure Speech Services 配置:**
```json
{
  "STT_API_Config": {
    "API_Key": "your-azure-speech-key",
    "API_Base_URL": "https://your-region.api.cognitive.microsoft.com",
    "Model": "whisper",
    "Provider_Type": "azure",
    "Custom_Headers": {
      "Ocp-Apim-Subscription-Key": "your-subscription-key"
    }
  }
}
```

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

### 支持的音频格式
- **原生支持**: MP3, WAV, FLAC, M4A, OGG
- **转换支持**: AMR, SILK(QQ语音), MP4音频等
- **自动检测**: 基于文件头智能识别格式

## 🔧 框架集成

### STT集成
```python
# 获取当前STT提供商
stt_provider = self.context.get_using_stt_provider()

# 调用语音识别
result = await stt_provider.get_text(audio_file_path)
```

### LLM集成
```python
# 获取当前LLM提供商(已配置人格)
llm_provider = self.context.get_using_provider()

# 生成智能回复(自动使用框架人格)
yield event.request_llm(
    prompt=prompt,
    session_id=session_id,
    contexts=context,
    conversation=conversation
)
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

插件会在AstrBot日志中输出详细的处理信息：

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

---

**注意**: 使用前请确保已正确配置AstrBot的STT和ChatLLM服务提供商。
