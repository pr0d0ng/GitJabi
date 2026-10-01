import os, logging
from dotenv import load_dotenv
load_dotenv()
from app.core.app import CoreApp
from app.routes import core, github, github_organization, auth, dashboard, dashboard_crs, knowledge_cloud

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()] # stdout으로 보냄 -> sh 파일이 이걸 낚아채서 파일에 저장
)
logging.info("Started process...")

if os.getenv('DEBUG', "false").lower() == 'true':
    logging.info("Debugging is TRUE")
    print('Debugging is TRUE')
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)


app = CoreApp(
    title="Gitjabi Backend API", 
    version="0.1.0"
)
app.set_middleware(
    allow_origins=[
        "localhost",
        "127.0.0.1",
        "https://dt-final-api-management.azure-api.net", 
        "https://v0-gitjabi-frontend-react.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.init_logging(
    development=True
)
#------------------
#   라우터 등록
#------------------
app.include_router(core.router)
app.include_router(github.router)
app.include_router(github_organization.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(dashboard_crs.router)
app.include_router(knowledge_cloud.router)



@app.get("/api")
async def root():
    return {"message": "Welcome, V1"}
