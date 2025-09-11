## Database Migration with Alembic (FastAPI)

Quick guide to setup and run Alembic migrations in a FastAPI project.


### 1. Initialize Alembic

```bash
alembic init alembic
````

* Creates `alembic/` folder and `alembic.ini`.


### 2. Configure Alembic

#### a. `alembic.ini`

Set your database URL:

```ini
sqlalchemy.url = postgresql://user:password@localhost/mydb
```

#### b. `env.py`

Import SQLAlchemy metadata for autogenerate:

```python
from app.entities.base import Base
target_metadata = Base.metadata

```

---

### 3. Create Migration

#### a. Auto from models

```bash
alembic revision --autogenerate -m "create initial tables"
```

* Alembic generates a file in `alembic/versions/`.
* Check the migration file before running.

#### b. Manual

```bash
alembic revision -m "add new column to user table"
```

* Edit manually if needed.

---

### 4. Apply Migration

```bash
alembic upgrade head
```

* `head` = latest version



## Other Tutorial

### Ingest file

```bash
python app/utils/ingest_docs.py
python app/utils/ingest_image.py
python -m app.utils.ingest_file
```