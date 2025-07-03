from app.controllers.database import init_database
from app.controllers.tasks import TasksController
from app.controllers.projects import ProjectsController
from app.controllers.scriptures import ScripturesController
from app.controllers.drafts import DraftsController
from app.controllers.lang_codes import LangCodesController

# Initialize database on module import
unpopulated = init_database()

# Controllers for database operations
tasks_controller = TasksController()
projects_controller = ProjectsController()
scriptures_controller = ScripturesController()
drafts_controller = DraftsController()
lang_codes_controller = LangCodesController()
