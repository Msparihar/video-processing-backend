from app.celery_app import celery_app


@celery_app.task(name="app.tasks.echo")
def echo(message: str) -> dict:
    return {"message": message}
