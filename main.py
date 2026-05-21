import argparse

from app.config import load_config
from app.dialogue import run_consultation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="智能问诊系统命令行入口")
    parser.add_argument(
        "--config",
        default=None,
        help="项目配置文件路径，默认使用 config/project.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    run_consultation(config)


if __name__ == "__main__":
    main()
