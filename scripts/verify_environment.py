import importlib


PACKAGES = [
    "numpy",
    "scipy",
    "pandas",
    "sklearn",
    "matplotlib",
    "open3d",
    "laspy",
    "torch",
]


def main() -> None:
    for package in PACKAGES:
        module = importlib.import_module(package)
        version = getattr(module, "__version__", "unknown")
        print(f"{package}: {version}")

    import torch

    print(f"cuda_available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"cuda_device: {torch.cuda.get_device_name(0)}")


if __name__ == "__main__":
    main()
