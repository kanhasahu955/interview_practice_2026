"""Browser HTML pages (Jinja2)."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.db import get_db
from app.deps import get_current_browser_user_optional
from app.modules.auth.model import User, UserRole
from app.schema.auth import UserCreate
from app.schema.blog import BlogPostCreate
from app.schema.coding import CodingProblemCreate
from app.schema.qa import AnswerCreate, QuestionCreate
from app.schema.syllabus import SyllabusItemCreate, SyllabusModuleCreate
from app.services.auth_service import PASSWORD_TOO_LONG_CODE, PASSWORD_TOO_LONG_MESSAGE, get_auth_service
from app.services.blog_service import get_blog_service
from app.services.chat_service import get_chat_service
from app.services.coding_service import get_coding_service
from app.services.qa_service import get_qa_service
from app.services.syllabus_service import get_syllabus_service
from app.utils.markdown import pygments_css, render_markdown


class PagesRoutes:
    def __init__(self, settings: Settings) -> None:
        self.router = APIRouter(tags=["PAGES"])
        self._templates = Jinja2Templates(directory=str(settings.templates_root))
        self._templates.env.filters["markdown"] = render_markdown
        self._templates.env.globals["pygments_css"] = pygments_css
        self._settings = settings
        self._auth = get_auth_service()
        self._blog = get_blog_service()
        self._chat = get_chat_service()
        self._coding = get_coding_service()
        self._qa = get_qa_service()
        self._syllabus = get_syllabus_service()
        self._register()

    def _template_context(
        self,
        request: Request,
        *,
        title: str,
        current_user: User | None,
        **extra: object,
    ) -> dict[str, object]:
        return {
            "request": request,
            "title": title,
            "api_prefix": self._settings.api_v1_prefix,
            "current_user": current_user,
            "notice": request.query_params.get("notice"),
            "error": request.query_params.get("error"),
            **extra,
        }

    @staticmethod
    def _redirect(path: str, *, notice: str | None = None, error: str | None = None) -> RedirectResponse:
        query: dict[str, str] = {}
        if notice:
            query["notice"] = notice
        if error:
            query["error"] = error
        location = f"{path}?{urlencode(query)}" if query else path
        return RedirectResponse(url=location, status_code=status.HTTP_303_SEE_OTHER)

    def _set_auth_cookie(self, response: RedirectResponse, token: str) -> None:
        max_age = self._settings.access_token_expire_minutes * 60
        response.set_cookie(
            key=self._settings.session_cookie_name,
            value=token,
            max_age=max_age,
            httponly=True,
            secure=self._settings.session_cookie_secure,
            samesite=self._settings.session_cookie_samesite,
            path="/",
        )

    def _clear_auth_cookie(self, response: RedirectResponse) -> None:
        response.delete_cookie(
            key=self._settings.session_cookie_name,
            path="/",
            samesite=self._settings.session_cookie_samesite,
        )

    @staticmethod
    def _safe_next(next_path: str | None, fallback: str = "/profile") -> str:
        if not next_path:
            return fallback
        if not next_path.startswith("/") or next_path.startswith("//"):
            return fallback
        return next_path

    def _login_redirect(self, next_path: str) -> RedirectResponse:
        return self._redirect(f"/auth/login?{urlencode({'next': self._safe_next(next_path)})}")

    @staticmethod
    def _can_access_dashboard(user: User | None) -> bool:
        return bool(user and user.role in (UserRole.author, UserRole.admin))

    def _register(self) -> None:
        r = self.router
        tpl = self._templates
        auth = self._auth
        blog = self._blog
        chat = self._chat
        coding = self._coding
        qa = self._qa
        syllabus = self._syllabus

        @r.get("/", summary="Home page (HTML)", response_description="HTML document (`text/html`).")
        async def index(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            modules = await syllabus.list_modules(session)
            posts = await blog.list_posts(session, user=current_user)
            problems = await coding.list_problems(session)
            questions = await qa.list_questions(session)
            room, messages = await chat.list_messages(session, limit=10)
            return tpl.TemplateResponse(
                "index.html",
                self._template_context(
                    request,
                    title=self._settings.app_name,
                    current_user=current_user,
                    modules=modules[:4],
                    posts=posts[:4],
                    problems=problems[:4],
                    questions=questions[:5],
                    chat_room=room,
                    chat_messages=[chat.serialize_message(message, room_slug=room.slug) for message in messages[-5:]],
                ),
            )

        @r.get("/study", summary="Study syllabus page", response_description="HTML document (`text/html`).")
        async def study_index(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            modules = await syllabus.list_modules(session)
            return tpl.TemplateResponse(
                "study/index.html",
                self._template_context(request, title="Python Study Roadmap", current_user=current_user, modules=modules),
            )

        @r.get("/study/modules/{module_id}", summary="Study module page", response_description="HTML document (`text/html`).")
        async def study_module_detail(
            module_id: int,
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            module = await syllabus.get_module(session, module_id)
            if module is None:
                return self._redirect("/study", error="Module not found.")
            return tpl.TemplateResponse(
                "study/module.html",
                self._template_context(
                    request,
                    title=module.title,
                    current_user=current_user,
                    module=module,
                ),
            )

        @r.get("/blogs", summary="Blog listing page", response_description="HTML document (`text/html`).")
        async def blog_index(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            posts = await blog.list_posts(session, user=current_user)
            return tpl.TemplateResponse(
                "blog/list.html",
                self._template_context(request, title="Python Blogs", current_user=current_user, posts=posts),
            )

        @r.get("/blogs/{slug}", summary="Blog detail page", response_description="HTML document (`text/html`).")
        async def blog_detail(
            slug: str,
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            post = await blog.get_post_by_slug(session, slug, user=current_user)
            if post is None:
                return self._redirect("/blogs", error="Blog post not found.")
            return tpl.TemplateResponse(
                "blog/detail.html",
                self._template_context(request, title=post.title, current_user=current_user, post=post),
            )

        @r.get("/coding", summary="Coding challenges page", response_description="HTML document (`text/html`).")
        async def coding_index(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            problems = await coding.list_problems(session)
            return tpl.TemplateResponse(
                "coding/list.html",
                self._template_context(request, title="Python Coding Challenges", current_user=current_user, problems=problems),
            )

        @r.get("/coding/{problem_id}", summary="Coding challenge detail", response_description="HTML document (`text/html`).")
        async def coding_detail(
            problem_id: int,
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            problem = await coding.get_problem(session, problem_id)
            if problem is None:
                return self._redirect("/coding", error="Coding problem not found.")
            return tpl.TemplateResponse(
                "coding/detail.html",
                self._template_context(
                    request,
                    title=problem.title,
                    current_user=current_user,
                    problem=problem,
                ),
            )

        @r.get("/qa", summary="Q&A page", response_description="HTML document (`text/html`).")
        async def qa_index(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            questions = await qa.list_questions(session)
            return tpl.TemplateResponse(
                "qa/list.html",
                self._template_context(request, title="Python Questions and Answers", current_user=current_user, questions=questions),
            )

        @r.get("/qa/{question_id}", summary="Question detail page", response_description="HTML document (`text/html`).")
        async def qa_detail(
            question_id: int,
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            question = await qa.get_question(session, question_id)
            if question is None:
                return self._redirect("/qa", error="Question not found.")
            return tpl.TemplateResponse(
                "qa/detail.html",
                self._template_context(
                    request,
                    title=question.title,
                    current_user=current_user,
                    question=question,
                ),
            )

        @r.post("/qa/questions", summary="Create question from browser", response_description="Redirect to HTML page.")
        async def create_question_from_browser(
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
            title: str = Form(...),
            body_md: str = Form(...),
            difficulty: str = Form(default="medium"),
        ):
            if current_user is None:
                return self._login_redirect("/qa")
            try:
                question = await qa.create_question(
                    session,
                    QuestionCreate(title=title, body_md=body_md, difficulty=difficulty),
                    user=current_user,
                )
            except ValidationError:
                return self._redirect("/qa", error="Please fill in the question form correctly.")
            return self._redirect(f"/qa/{question.id}", notice="Question posted.")

        @r.post("/qa/{question_id}/answers", summary="Create answer from browser", response_description="Redirect to HTML page.")
        async def create_answer_from_browser(
            question_id: int,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
            body_md: str = Form(...),
            is_official: bool = Form(default=False),
        ):
            if current_user is None:
                return self._login_redirect(f"/qa/{question_id}")
            try:
                await qa.create_answer(
                    session,
                    question_id,
                    AnswerCreate(body_md=body_md, is_official=is_official),
                    user=current_user,
                )
            except ValidationError:
                return self._redirect(f"/qa/{question_id}", error="Please provide an answer before submitting.")
            except ValueError:
                return self._redirect("/qa", error="Question not found.")
            return self._redirect(f"/qa/{question_id}", notice="Answer added.")

        @r.post("/qa/answers/{answer_id}/accept", summary="Accept answer from browser", response_description="Redirect to HTML page.")
        async def accept_answer_from_browser(
            answer_id: int,
            question_id: int = Form(...),
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            if current_user is None:
                return self._login_redirect(f"/qa/{question_id}")
            try:
                await qa.accept_answer(session, answer_id, user=current_user)
            except ValueError as exc:
                if str(exc) == "forbidden":
                    return self._redirect(f"/qa/{question_id}", error="Only the question author can accept answers.")
                return self._redirect(f"/qa/{question_id}", error="Answer not found.")
            return self._redirect(f"/qa/{question_id}", notice="Accepted answer updated.")

        @r.get("/auth/login", summary="Login page", response_description="HTML document (`text/html`).")
        async def login_page(request: Request, current_user: User | None = Depends(get_current_browser_user_optional)):
            if current_user:
                return self._redirect("/profile")
            next_path = self._safe_next(request.query_params.get("next"), "/profile")
            return tpl.TemplateResponse(
                "auth/login.html",
                self._template_context(request, title="Login", current_user=None, next_path=next_path),
            )

        @r.post("/auth/login", summary="Login from browser", response_description="Redirect to HTML page.")
        async def login_from_browser(
            username: str = Form(...),
            password: str = Form(...),
            next_path: str = Form(default="/profile"),
            session: AsyncSession = Depends(get_db),
        ):
            try:
                token = await auth.login_token(session, username=username, password=password)
            except ValueError as exc:
                message = "Invalid credentials."
                if str(exc) == "inactive":
                    message = "This account is inactive."
                if str(exc) == PASSWORD_TOO_LONG_CODE:
                    message = PASSWORD_TOO_LONG_MESSAGE
                return self._redirect("/auth/login", error=message)
            destination = self._safe_next(next_path, "/profile")
            response = self._redirect(destination, notice="Welcome back.")
            self._set_auth_cookie(response, token.access_token)
            return response

        @r.get("/auth/register", summary="Register page", response_description="HTML document (`text/html`).")
        async def register_page(request: Request, current_user: User | None = Depends(get_current_browser_user_optional)):
            if current_user:
                return self._redirect("/profile")
            return tpl.TemplateResponse(
                "auth/register.html",
                self._template_context(request, title="Create account", current_user=None),
            )

        @r.post("/auth/register", summary="Register from browser", response_description="Redirect to HTML page.")
        async def register_from_browser(
            email: str = Form(...),
            password: str = Form(...),
            full_name: str = Form(default=""),
            session: AsyncSession = Depends(get_db),
        ):
            try:
                body = UserCreate(email=email, password=password, full_name=full_name or None)
                user = await auth.register_user(session, body)
            except ValidationError as exc:
                errors = exc.errors()
                password_errors = [
                    str(error.get("msg", ""))
                    for error in errors
                    if "password" in [str(part) for part in error.get("loc", ())]
                ]
                if password_errors:
                    return self._redirect("/auth/register", error=password_errors[0])
                return self._redirect("/auth/register", error="Please provide a valid email and password.")
            except ValueError as exc:
                if str(exc) == "email_taken":
                    return self._redirect("/auth/register", error="That email is already registered.")
                if str(exc) == PASSWORD_TOO_LONG_CODE:
                    return self._redirect("/auth/register", error=PASSWORD_TOO_LONG_MESSAGE)
                raise

            token = auth.create_access_token(subject=str(user.id), role=user.role.value)
            response = self._redirect("/profile", notice="Account created.")
            self._set_auth_cookie(response, token)
            return response

        @r.post("/auth/logout", summary="Logout from browser", response_description="Redirect to HTML page.")
        async def logout_from_browser():
            response = self._redirect("/", notice="You have been logged out.")
            self._clear_auth_cookie(response)
            return response

        @r.get("/profile", summary="Profile page", response_description="HTML document (`text/html`).")
        async def profile_page(request: Request, current_user: User | None = Depends(get_current_browser_user_optional)):
            if current_user is None:
                return self._login_redirect("/profile")
            return tpl.TemplateResponse(
                "profile/detail.html",
                self._template_context(
                    request,
                    title="Your profile",
                    current_user=current_user,
                    can_access_dashboard=self._can_access_dashboard(current_user),
                ),
            )

        @r.get("/dashboard", summary="Author dashboard page", response_description="HTML document (`text/html`).")
        async def dashboard_page(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            if current_user is None:
                return self._login_redirect("/dashboard")
            if not self._can_access_dashboard(current_user):
                return self._redirect("/profile", error="Author or admin access is required.")
            modules = await syllabus.list_modules(session)
            posts = await blog.list_posts(session, user=current_user)
            problems = await coding.list_problems(session)
            questions = await qa.list_questions(session)
            return tpl.TemplateResponse(
                "dashboard/index.html",
                self._template_context(
                    request,
                    title="Author dashboard",
                    current_user=current_user,
                    modules=modules,
                    posts=posts,
                    problems=problems,
                    questions=questions[:10],
                ),
            )

        @r.post("/dashboard/syllabus/modules", summary="Create syllabus module from dashboard")
        async def dashboard_create_module(
            current_user: User | None = Depends(get_current_browser_user_optional),
            session: AsyncSession = Depends(get_db),
            title: str = Form(...),
            description: str = Form(default=""),
            sort_order: int = Form(default=0),
        ):
            if current_user is None:
                return self._login_redirect("/dashboard")
            if not self._can_access_dashboard(current_user):
                return self._redirect("/profile", error="Author or admin access is required.")
            try:
                await syllabus.create_module(
                    session,
                    SyllabusModuleCreate(title=title, description=description or None, sort_order=sort_order),
                )
            except ValidationError:
                return self._redirect("/dashboard", error="Please fill in the module form correctly.")
            return self._redirect("/dashboard", notice="Syllabus module created.")

        @r.post("/dashboard/syllabus/items", summary="Create syllabus item from dashboard")
        async def dashboard_create_item(
            current_user: User | None = Depends(get_current_browser_user_optional),
            session: AsyncSession = Depends(get_db),
            module_id: int = Form(...),
            title: str = Form(...),
            content_md: str = Form(...),
            sort_order: int = Form(default=0),
        ):
            if current_user is None:
                return self._login_redirect("/dashboard")
            if not self._can_access_dashboard(current_user):
                return self._redirect("/profile", error="Author or admin access is required.")
            try:
                item = await syllabus.create_item(
                    session,
                    module_id,
                    SyllabusItemCreate(title=title, content_md=content_md, sort_order=sort_order),
                )
            except ValidationError:
                return self._redirect("/dashboard", error="Please fill in the lesson form correctly.")
            except ValueError:
                return self._redirect("/dashboard", error="Selected syllabus module was not found.")
            return self._redirect(f"/study/modules/{item.module_id}", notice="Lesson created.")

        @r.post("/dashboard/blogs", summary="Create blog post from dashboard")
        async def dashboard_create_blog(
            current_user: User | None = Depends(get_current_browser_user_optional),
            session: AsyncSession = Depends(get_db),
            title: str = Form(...),
            slug: str = Form(...),
            body_md: str = Form(...),
            published: bool = Form(default=False),
        ):
            if current_user is None:
                return self._login_redirect("/dashboard")
            if not self._can_access_dashboard(current_user):
                return self._redirect("/profile", error="Author or admin access is required.")
            try:
                post = await blog.create_post(
                    session,
                    BlogPostCreate(title=title, slug=slug, body_md=body_md, published=published),
                    author=current_user,
                )
            except ValidationError:
                return self._redirect("/dashboard", error="Please fill in the blog form correctly.")
            except ValueError:
                return self._redirect("/dashboard", error="That blog slug already exists.")
            return self._redirect(f"/blogs/{post.slug}", notice="Blog post saved.")

        @r.post("/dashboard/coding", summary="Create coding problem from dashboard")
        async def dashboard_create_coding(
            current_user: User | None = Depends(get_current_browser_user_optional),
            session: AsyncSession = Depends(get_db),
            title: str = Form(...),
            problem_md: str = Form(...),
            difficulty: str = Form(default="medium"),
            starter_code: str = Form(default=""),
            hints_md: str = Form(default=""),
        ):
            if current_user is None:
                return self._login_redirect("/dashboard")
            if not self._can_access_dashboard(current_user):
                return self._redirect("/profile", error="Author or admin access is required.")
            try:
                problem = await coding.create_problem(
                    session,
                    CodingProblemCreate(
                        title=title,
                        problem_md=problem_md,
                        difficulty=difficulty,
                        starter_code=starter_code or None,
                        hints_md=hints_md or None,
                    ),
                )
            except ValidationError:
                return self._redirect("/dashboard", error="Please fill in the coding problem form correctly.")
            return self._redirect(f"/coding/{problem.id}", notice="Coding challenge created.")

        @r.get("/chat", summary="Realtime chat page", response_description="HTML document (`text/html`).")
        async def chat_page(
            request: Request,
            session: AsyncSession = Depends(get_db),
            current_user: User | None = Depends(get_current_browser_user_optional),
        ):
            room, messages = await chat.list_messages(session)
            return tpl.TemplateResponse(
                "chat/index.html",
                self._template_context(
                    request,
                    title=room.title,
                    current_user=current_user,
                    chat_room=room,
                    chat_messages=[chat.serialize_message(message, room_slug=room.slug) for message in messages],
                    chat_ws_path=f"{self._settings.api_v1_prefix}/chat/ws/rooms/{room.slug}",
                ),
            )
