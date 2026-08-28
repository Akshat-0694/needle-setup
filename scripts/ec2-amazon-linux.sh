#!/usr/bin/env bash
set -euo pipefail
sudo dnf update -y
sudo dnf install -y docker git curl
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
echo "Log out and SSH back in before using docker without sudo."
