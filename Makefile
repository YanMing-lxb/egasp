.PHONY: all clean html rst whl pack inswhl upload pot mo poup excel-addin app_builder release-build

# 变量定义
UV_RUN = @uv run python
TOOLS_DIR = ./tools

# 默认目标
all:
	$(UV_RUN) $(TOOLS_DIR)/make.py all

# 清理
clean:
	$(UV_RUN) $(TOOLS_DIR)/utils.py clean

# 文档生成
html:
	$(UV_RUN) $(TOOLS_DIR)/make.py html

rst:
	$(UV_RUN) $(TOOLS_DIR)/make.py rst

# 构建wheel包
whl: clean
	@uv build

# 打包可执行文件
pack:
	$(UV_RUN) $(TOOLS_DIR)/pack.py pack

# 安装wheel包测试
inswhl:
	$(UV_RUN) $(TOOLS_DIR)/make.py inswhl

# 上传标签
upload:
	$(UV_RUN) $(TOOLS_DIR)/make.py upload

# 国际化
pot mo poup:
	$(UV_RUN) $(TOOLS_DIR)/lang_tool.py $@

# 构建Excel/WPS插件
excel-addin:
	@echo "Building Excel/WPS integration add-in..."
	$(UV_RUN) $(TOOLS_DIR)/build_addin.py

# 构建完整应用
app_builder:
	@echo "Building full application package..."
	$(UV_RUN) $(TOOLS_DIR)/app_builder.py

# 完整发布构建（包括插件和完整应用）
release-build: whl pack excel-addin app_builder
	@echo "Release excel-addin complete! Ready for publishing."

	
