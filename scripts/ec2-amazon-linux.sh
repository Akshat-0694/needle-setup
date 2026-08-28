#!/usr/bin/env bash
set -euo pipefail

echo "Installing Docker and Git on Amazon Linux 2023..."
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

echo
echo "Docker:"
docker --version || true
echo
echo "IMPORTANT: log out and SSH back in before using docker without sudo."
