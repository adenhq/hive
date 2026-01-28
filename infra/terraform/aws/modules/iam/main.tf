terraform {
  required_version = ">= 1.5.0"
}

data "aws_iam_policy_document" "task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-task-exec"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "task_policy" {
  dynamic "statement" {
    for_each = length(var.secrets_manager_arns) > 0 ? [1] : []
    content {
      actions   = ["secretsmanager:GetSecretValue"]
      resources = var.secrets_manager_arns
    }
  }
}

resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
}

resource "aws_iam_policy" "task" {
  count  = length(var.secrets_manager_arns) > 0 ? 1 : 0
  name   = "${var.name_prefix}-task-secrets"
  policy = data.aws_iam_policy_document.task_policy.json
}

resource "aws_iam_role_policy_attachment" "task" {
  count      = length(var.secrets_manager_arns) > 0 ? 1 : 0
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task[0].arn
}