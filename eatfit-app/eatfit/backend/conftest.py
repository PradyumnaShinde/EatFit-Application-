"""Test setup: points the app at a throwaway database before anything is imported."""
import os

os.environ.setdefault("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eatfit_test")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["AUTH_MODE"] = "dev"
os.environ["ENV"] = "test"
