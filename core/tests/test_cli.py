"""
Tests for CLI module.

Run with:
    cd core
    pytest tests/test_cli.py -v
"""

from unittest.mock import MagicMock, patch

from framework.cli import main


class TestCLIMain:
    """Test the main CLI function."""

    @patch("framework.runner.cli.register_commands")
    @patch("framework.testing.cli.register_testing_commands")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_main_with_valid_command(
        self, mock_exit, mock_parse_args, mock_register_testing, mock_register_runner
    ):
        """Test main function with a valid command that has a func attribute.

        Validates that when a user provides a valid command with a func handler:
        - Both runner and testing command subparsers are registered
        - Argument parsing is called correctly
        - The command's func is invoked with parsed arguments
        - sys.exit is called with the return value (0 for success)
        """
        # Mock parsed args with a func
        mock_args = MagicMock()
        mock_args.func = MagicMock(return_value=0)
        mock_parse_args.return_value = mock_args

        # Call main
        main()

        # Verify subparsers were registered
        mock_register_runner.assert_called_once()
        mock_register_testing.assert_called_once()

        # Verify parse_args was called
        mock_parse_args.assert_called_once()

        # Verify func was called and sys.exit was called with its return value
        mock_args.func.assert_called_once_with(mock_args)
        mock_exit.assert_called_once_with(0)

    @patch("framework.runner.cli.register_commands")
    @patch("framework.testing.cli.register_testing_commands")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_main_with_command_returning_non_zero(
        self, mock_exit, mock_parse_args, mock_register_testing, mock_register_runner
    ):
        """Test main function when command func returns non-zero exit code.

        Validates error handling and propagation:
        - When a command handler returns a non-zero exit code (e.g., 1)
        - sys.exit is called with that exact exit code
        - Errors from command execution are properly communicated to the OS
        """
        # Mock parsed args with a func that returns 1
        mock_args = MagicMock()
        mock_args.func = MagicMock(return_value=1)
        mock_parse_args.return_value = mock_args

        # Call main
        main()

        # Verify sys.exit was called with 1
        mock_exit.assert_called_once_with(1)

    @patch("framework.runner.cli.register_commands")
    @patch("framework.testing.cli.register_testing_commands")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_without_func_attribute(
        self, mock_parse_args, mock_register_testing, mock_register_runner
    ):
        """Test main function when parsed args has no func attribute.

        Validates graceful handling of edge cases:
        - When a user provides no subcommand (argparse should require one)
        - When parsed args lacks a func attribute (defensive check)
        - The program should not crash but handle this gracefully
        - Command registration should still occur before this check
        """
        # Mock parsed args without func
        mock_args = MagicMock(spec=[])  # No func attribute
        mock_parse_args.return_value = mock_args

        # Call main - should not raise exception, just return
        main()

        # Verify subparsers were registered
        mock_register_runner.assert_called_once()
        mock_register_testing.assert_called_once()

        # Verify parse_args was called
        mock_parse_args.assert_called_once()

    @patch("framework.runner.cli.register_commands")
    @patch("framework.testing.cli.register_testing_commands")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_main_parser_configuration(
        self, mock_exit, mock_parse_args, mock_register_testing, mock_register_runner
    ):
        """Test that the argument parser is configured correctly.

        Validates CLI argument parser setup and configuration:
        - ArgumentParser is initialized with correct description
        - --model argument is added with correct default and help text
        - Subparsers are created with required=True (forces subcommand)
        - Parser configuration matches CLI requirements for Goal Agent
        """
        # Mock parse_args to avoid actual parsing
        mock_args = MagicMock()
        mock_args.func = MagicMock(return_value=0)
        mock_parse_args.return_value = mock_args

        with patch("argparse.ArgumentParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser_class.return_value = mock_parser
            mock_parser.parse_args.return_value = mock_args

            # Call main
            main()

            # Verify ArgumentParser was created with correct description
            mock_parser_class.assert_called_once_with(
                description="Goal Agent - Build and run goal-driven agents"
            )

            # Verify add_argument was called for --model
            mock_parser.add_argument.assert_called_once_with(
                "--model",
                default="claude-haiku-4-5-20251001",
                help="Anthropic model to use",
            )

            # Verify subparsers were created
            mock_parser.add_subparsers.assert_called_once_with(dest="command", required=True)

            # Verify sys.exit was called
            mock_exit.assert_called_once_with(0)

    @patch("framework.runner.cli.register_commands")
    @patch("framework.testing.cli.register_testing_commands")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_main_imports_and_registers_commands(
        self, mock_exit, mock_parse_args, mock_register_testing, mock_register_runner
    ):
        """Test that the correct modules are imported and their functions called.

        Validates command registration and module integration:
        - framework.runner.cli.register_commands is called to register runner commands
        - framework.testing.cli.register_testing_commands is called for testing commands
        - Commands are properly registered with the argument parser
        - sys.exit is called with the return value from command execution
        """
        # Mock parsed args
        mock_args = MagicMock()
        mock_args.func = MagicMock(return_value=0)
        mock_parse_args.return_value = mock_args

        # Call main
        main()

        # Verify the imports happened by checking the mocks were called
        # (The actual imports happen inside main())
        mock_register_runner.assert_called_once()
        mock_register_testing.assert_called_once()

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(0)

