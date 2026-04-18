#!/bin/bash
# Ativar ambiente do workspace
cd ~/claude-workspace
source venv/bin/activate
export WORKSPACE_ROOT=~/claude-workspace
echo "Workspace ativado. Use: python3 cli.py --help"
