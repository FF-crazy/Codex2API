# Codex2API 重构计划

## 当前状态

### ✅ 已完成
- **Pydantic模型层** (`src/codex2api/models/`): 完整的认证、请求、响应模型
  - `auth.py`: TokenData, AuthBundle, PkceCodes等认证模型
  - `requests.py`: ChatCompletionRequest, CompletionRequest等请求模型  
  - `responses.py`: ChatCompletionResponse, ModelsResponse等响应模型
  - 完全兼容OpenAI API规范，移除了Ollama依赖

### ❌ 待完成的核心模块

#### 1. 认证模块 (`src/codex2api/auth/`)
**当前状态**: 空文件
**需要实现**:
- `oauth.py`: OAuth认证流程实现
- `token_manager.py`: Token管理和刷新
- `session.py`: 会话管理
- `middleware.py`: FastAPI认证中间件

#### 2. 核心模块 (`src/codex2api/core/`)
**当前状态**: 空文件
**需要实现**:
- `config.py`: 应用配置管理
- `exceptions.py`: 自定义异常类
- `logging.py`: 日志配置
- `security.py`: 安全相关工具

#### 3. API路由 (`src/codex2api/api/v1/`)
**当前状态**: 空文件
**需要实现**:
- `chat.py`: 聊天完成API端点
- `completions.py`: 文本完成API端点
- `models.py`: 模型列表API端点
- `auth.py`: 认证相关API端点

#### 4. 服务层 (`src/codex2api/services/`)
**当前状态**: 空文件
**需要实现**:
- `chatgpt_client.py`: ChatGPT客户端封装
- `openai_proxy.py`: OpenAI API代理服务
- `model_manager.py`: 模型管理服务
- `conversation.py`: 对话管理服务

#### 5. 工具模块 (`src/codex2api/utils/`)
**当前状态**: 空文件
**需要实现**:
- `http_client.py`: HTTP客户端工具
- `json_utils.py`: JSON处理工具
- `validation.py`: 数据验证工具
- `streaming.py`: 流式响应处理

#### 6. 主应用 (`src/codex2api/`)
**需要更新**:
- `__init__.py`: 版本信息和包导出
- `main.py`: FastAPI应用入口点
- `app.py`: 应用工厂函数

## 详细重构计划

### 阶段1: 核心基础设施 (优先级: 高)
1. **配置管理** (`core/config.py`)
   - 环境变量管理
   - 配置验证
   - 默认值设置

2. **异常处理** (`core/exceptions.py`)
   - 自定义异常类
   - 错误码定义
   - 异常处理器

3. **日志系统** (`core/logging.py`)
   - 结构化日志
   - 日志级别配置
   - 请求追踪

### 阶段2: 认证系统 (优先级: 高)
1. **OAuth流程** (`auth/oauth.py`)
   - PKCE实现
   - 授权码交换
   - Token获取

2. **Token管理** (`auth/token_manager.py`)
   - Token存储
   - 自动刷新
   - 过期检测

3. **认证中间件** (`auth/middleware.py`)
   - 请求认证
   - Token验证
   - 权限检查

### 阶段3: 服务层 (优先级: 高)
1. **ChatGPT客户端** (`services/chatgpt_client.py`)
   - 会话管理
   - 请求封装
   - 错误处理

2. **OpenAI代理** (`services/openai_proxy.py`)
   - 请求转换
   - 响应格式化
   - 流式处理

### 阶段4: API端点 (优先级: 中)
1. **聊天API** (`api/v1/chat.py`)
   - `/v1/chat/completions`
   - 流式和非流式响应
   - 参数验证

2. **完成API** (`api/v1/completions.py`)
   - `/v1/completions`
   - 兼容性支持

3. **模型API** (`api/v1/models.py`)
   - `/v1/models`
   - 模型列表

### 阶段5: 工具和优化 (优先级: 低)
1. **HTTP工具** (`utils/http_client.py`)
2. **流式处理** (`utils/streaming.py`)
3. **性能优化**
4. **监控和指标**

## 技术要求

### 依赖管理
- FastAPI: Web框架
- Pydantic: 数据验证 (已完成)
- httpx: HTTP客户端
- structlog: 结构化日志
- python-multipart: 文件上传支持

### 代码规范
- 类型提示: 所有函数和方法
- 文档字符串: Google风格
- 错误处理: 统一异常体系
- 测试覆盖: 单元测试和集成测试

### 架构原则
- 依赖注入: 便于测试和扩展
- 分层架构: 清晰的职责分离
- 配置驱动: 环境变量配置
- 异步优先: 高性能I/O处理

## 下一步行动

1. **立即开始**: 核心配置和异常处理
2. **紧接着**: 认证系统实现
3. **然后**: 服务层和API端点
4. **最后**: 工具优化和测试完善

## 预估工作量

- **阶段1-2**: 2-3天 (核心基础设施 + 认证)
- **阶段3**: 2-3天 (服务层)
- **阶段4**: 2-3天 (API端点)
- **阶段5**: 1-2天 (工具和优化)

**总计**: 约7-11天的开发工作

## 风险和挑战

1. **ChatGPT API变化**: 需要持续适配
2. **认证复杂性**: OAuth流程实现
3. **性能要求**: 流式响应处理
4. **兼容性**: 与现有ChatMock代码的兼容

您希望我从哪个阶段开始继续重构工作？
