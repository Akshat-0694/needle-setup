#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Updating packages..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git

echo "[2/4] Installing Docker..."
sudo install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" |
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[3/4] Enabling Docker..."
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

echo "[4/4] Done."
echo "Log out and back in once so the docker group change takes effect."
echo "Then run: docker --version && docker compose version"
