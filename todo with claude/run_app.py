#!/usr/bin/env python
"""스마트 태스크 매니저 데스크톱 앱 실행."""

import os
import sys

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from gui.app import TaskManagerApp

if __name__ == "__main__":
    app = TaskManagerApp()
    app.run()
