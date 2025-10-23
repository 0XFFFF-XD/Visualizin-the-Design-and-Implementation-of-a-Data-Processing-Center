# 数据处理与可视化中心

这是一个基于Python和Web技术实现的数据处理与可视化中心，满足毕业设计要求的功能。

## 功能特性

1. **数据接入与处理层**
   - 支持CSV文件上传和管理
   - 提供数据预览功能
   - 实现数据源管理

2. **数据分析与服务层**
   - 提供数据过滤、排序、分组等处理功能
   - 支持常见的统计分析操作
   - 提供RESTful API接口

3. **可视化展示与交互层**
   - 支持多种图表类型（柱状图、折线图、饼图）
   - 提供交互式图表配置
   - 实现数据可视化展示

## 安装与运行

### 环境要求

- Python 3.7+
- pip包管理器

### 安装步骤

1. 克隆或下载项目代码

2. 安装依赖包：
   ```
   pip install -r requirements.txt
   ```

3. 运行应用：
   ```
   python app.py
   ```

4. 在浏览器中访问 `http://localhost:5000`

## 使用说明

1. **数据源管理**：在"数据源管理"页面可以上传CSV文件，并预览数据内容
2. **数据处理**：在"数据处理"页面可以选择数据源，添加处理操作（过滤、排序、分组），并执行处理
3. **数据可视化**：在"数据可视化"页面可以选择数据源和图表类型，配置图表参数并生成可视化图表

## 目录结构

```
.
├── app.py              # Flask主应用
├── requirements.txt    # 项目依赖
├── README.md           # 说明文档
├── data/               # 数据存储目录
├── templates/          # HTML模板目录
│   ├── base.html       # 基础模板
│   ├── index.html      # 主页
│   ├── data_sources.html # 数据源管理页面
│   ├── data_processing.html # 数据处理页面
│   └── visualization.html # 数据可视化页面
└── static/             # 静态资源目录（CSS, JS, 图片等）
```

## 技术栈

- 后端：Python + Flask
- 数据处理：Pandas
- 前端：HTML5 + Bootstrap 5 + JavaScript
- 图表库：Chart.js
- 数据交换格式：JSON

## API接口

- `GET /api/data_sources` - 获取所有数据源
- `POST /api/upload` - 上传数据文件
- `GET /api/data/<filename>/preview` - 预览数据
- `POST /api/process` - 处理数据
- `GET /api/visualization/<filename>` - 获取可视化数据

## 注意事项

1. 当前版本仅支持CSV格式文件
2. 数据文件存储在本地[data](file:///e:/毕业设计/可视化展示数据处理中心的设计和实现/data)目录中
3. 处理后的数据也会保存在[data](file:///e:/毕业设计/可视化展示数据处理中心的设计和实现/data)目录中，文件名前缀为"processed_"