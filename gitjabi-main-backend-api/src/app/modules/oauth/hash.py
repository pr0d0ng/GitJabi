from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

DUMMY_HASH = pwd_context.hash("dummy_password")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


if __name__ == "__main__":
    p = input('new password: ')
    print(hash_password(p))
