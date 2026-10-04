from pathlib import Path

from grpc_tools import protoc

ROOT = Path(__file__).resolve().parent
PROTO_DIR = ROOT / "proto"
TARGETS = [ROOT / "server", ROOT / "client"]


def main() -> None:
    for target in TARGETS:
        result = protoc.main([
            "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={target}",
            f"--grpc_python_out={target}",
            str(PROTO_DIR / "racing.proto"),
        ])
        if result != 0:
            raise SystemExit(f"Falha ao gerar código em {target}")
        print(f"Gerado em {target}")


if __name__ == "__main__":
    main()
