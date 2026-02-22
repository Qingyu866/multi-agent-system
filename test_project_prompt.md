# 测试项目：在线任务管理系统

## 项目概述
创建一个完整的在线任务管理系统（类似Trello），支持看板视图、任务拖拽、团队协作等功能。

## 功能需求

### 前端功能
1. **看板视图**
   - 支持多列看板（待办、进行中、已完成）
   - 任务卡片拖拽排序
   - 列的添加、删除、重命名

2. **任务管理**
   - 创建、编辑、删除任务
   - 任务详情：标题、描述、截止日期、优先级
   - 任务标签和分类

3. **用户界面**
   - 响应式设计，支持移动端
   - 深色/浅色主题切换
   - 流畅的动画效果

### 后端功能
1. **用户认证**
   - 用户注册、登录
   - JWT Token认证
   - 密码加密存储

2. **API接口**
   - RESTful API设计
   - 看板CRUD操作
   - 任务CRUD操作
   - 用户管理接口

3. **数据存储**
   - 用户数据表
   - 看板数据表
   - 任务数据表
   - 支持数据关联

### 部署要求
1. Docker容器化部署
2. 支持环境变量配置
3. 数据库持久化

## 技术栈
- 前端：React + TypeScript + TailwindCSS
- 后端：Python + FastAPI
- 数据库：PostgreSQL
- 部署：Docker + Docker Compose

## 预期触发的细分Agent
1. **Frontend Developer** - 实现React前端界面
2. **Backend Developer** - 实现FastAPI后端API
3. **Database Developer** - 设计PostgreSQL数据库
4. **DevOps Engineer** - 配置Docker部署
5. **UI/UX Designer** - 设计界面和交互

## 测试目标
1. 任务分析器正确识别项目类别
2. 任务路由器分配给正确的Agent
3. 各Agent按职责边界工作
4. 结果整合器正确合并输出
