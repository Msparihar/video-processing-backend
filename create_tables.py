from app.database import engine, Base
from app import models  # noqa: F401 - import models to register tables


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not existing).")


if __name__ == "__main__":
    main()
