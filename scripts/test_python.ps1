$PYTHON_CMD = "python"
$VerScript = "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))"
Write-Host "Running python..."
& $PYTHON_CMD -c $VerScript
Write-Host "Done"
