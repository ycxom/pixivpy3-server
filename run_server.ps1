# run_server.ps1

# 1. 激活虚拟环境 (使用专门的 .ps1 文件)
# 使用点源操作符 '.' 来确保脚本在当前会话中运行，从而修改当前Shell的环境变量。
Write-Host "Activating virtual environment using Activate.ps1..."
. .\venv\Scripts\Activate.ps1

# 2. 运行 Python 服务器
Write-Host "Starting Python server..."
python server.py

# 3. 停用虚拟环境
# Activate.ps1 成功运行后，它会在当前会话中创建 'deactivate' 函数。
Write-Host "Deactivating virtual environment..."
deactivate