resource "aws_security_group" "audit" {
  name        = "${var.environment}-audit"
  description = "Security group for the audit node"
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    Name = "${var.environment}-node-sg"
  }
}
