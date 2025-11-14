# Reflex Framework Patterns for Coding Agents

## Core Architecture Principles

### State Management Fundamentals

**CRITICAL**: State is the single source of truth. UI = f(State). Never manipulate DOM directly.

```python
class MyState(rx.State):
    count: int = 0  # Type annotations required
    items: list[str] = []  # Use proper type hints
    
    def increment(self):
        self.count += 1  # Reflex detects and syncs automatically
```

**Container Mutation Pattern** (IMPORTANT):
```python
# ❌ UNRELIABLE - may not trigger UI update
def add_item(self, item: str):
    self.items.append(item)

# ✅ RELIABLE - guarantees UI update
def add_item(self, item: str):
    self.items.append(item)
    self.items = list(self.items)  # Defensive reassignment
```

### Async/Loading Pattern (ESSENTIAL)

**ALWAYS use loading flags for operations that take >100ms**:

```python
class DataState(rx.State):
    loading: bool = False
    error: str = ""
    result: dict | None = None
    
    async def fetch_data(self):
        if self.loading:  # Prevent duplicate requests
            return
            
        self.loading = True
        self.error = ""
        try:
            # Async I/O work here
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/data")
                self.result = response.json()
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False  # ALWAYS in finally block
```

**UI Integration**:
```python
rx.cond(
    DataState.loading,
    rx.spinner(),
    rx.cond(
        DataState.error != "",
        rx.text(DataState.error, color="red"),
        rx.box(DataState.result)
    )
)
```

---

## Component Architecture

### Component Composition Pattern

**Break down into small, reusable functions**:

```python
def header() -> rx.Component:
    return rx.box(
        rx.heading("My App", size="lg"),
        rx.hstack(
            navigation_links(),
            user_menu(),
        ),
        bg="blue.500",
        p="1rem"
    )

def navigation_links() -> rx.Component:
    return rx.hstack(
        rx.link("Home", href="/"),
        rx.link("About", href="/about"),
        spacing="1rem"
    )

def user_menu() -> rx.Component:
    return rx.cond(
        AuthState.is_logged_in,
        rx.menu.root(
            rx.menu.trigger(rx.button(AuthState.username)),
            rx.menu.content(
                rx.menu.item("Profile", on_click=lambda: rx.redirect("/profile")),
                rx.menu.item("Logout", on_click=AuthState.logout),
            )
        ),
        rx.button("Login", on_click=lambda: rx.redirect("/login"))
    )

def index() -> rx.Component:
    return rx.vstack(
        header(),
        rx.box(
            # Page content
            min_height="80vh"
        ),
        footer(),
        width="100%"
    )
```

### Props Pattern (Data Passing)

```python
def product_card(
    name: str,
    price: float,
    image_url: str,
    on_add_to_cart: rx.EventHandler | None = None
) -> rx.Component:
    return rx.box(
        rx.image(src=image_url),
        rx.heading(name, size="md"),
        rx.text(f"${price:.2f}"),
        rx.button(
            "Add to Cart",
            on_click=on_add_to_cart or CartState.add_item(name)
        ),
        border="1px solid gray",
        p="1rem"
    )

# Usage with dynamic data
rx.foreach(
    ProductState.products,
    lambda p: product_card(p.name, p.price, p.image_url)
)
```

### Conditional Rendering

```python
# Simple boolean check
rx.cond(
    State.show_details,
    detailed_view(),
    summary_view()
)

# Multi-condition (nest rx.cond)
rx.cond(
    State.is_loading,
    rx.spinner(),
    rx.cond(
        State.data is not None,
        data_display(),
        rx.text("No data available")
    )
)

# Pattern matching equivalent
rx.match(
    State.view_mode,
    ("grid", grid_layout()),
    ("list", list_layout()),
    ("table", table_layout()),
    rx.text("Invalid view mode")  # default
)
```

---

## Layouts & Styling

### Layout Primitives (Use These)

```python
# Vertical stack (most common)
rx.vstack(
    component1(),
    component2(),
    spacing="1rem",  # Gap between items
    align="center",  # Horizontal alignment
    width="100%"
)

# Horizontal stack
rx.hstack(
    left_panel(),
    right_panel(),
    spacing="2rem",
    justify="space-between"  # Spread items apart
)

# Grid layout
rx.grid(
    *[card(i) for i in range(12)],
    columns="3",  # or {"base": "1", "md": "2", "lg": "3"}
    spacing="1rem"
)

# Flexible box (most control)
rx.box(
    content(),
    display="flex",
    flex_direction="column",
    align_items="center",
    justify_content="center",
    min_height="100vh"
)
```

### Responsive Design Pattern

```python
rx.box(
    rx.heading("Title", size={"base": "md", "lg": "xl"}),
    padding={"base": "1rem", "md": "2rem", "lg": "4rem"},
    width={"base": "100%", "md": "80%", "lg": "60%"},
    # Breakpoints: base (mobile), sm, md, lg, xl, 2xl
)

# Responsive stack direction
rx.stack(
    sidebar(),
    main_content(),
    direction={"base": "column", "md": "row"},  # Vertical on mobile, horizontal on desktop
    spacing="1rem"
)
```

### Theme Configuration

```python
# In main app file
app = rx.App(
    theme=rx.theme(
        appearance="light",  # or "dark"
        accent_color="blue",
        gray_color="slate",
        radius="medium",  # Button/card roundness
        scaling="100%"
    )
)

# Use theme tokens in components
rx.box(
    bg="accent.3",  # Uses theme accent color at opacity level 3
    color="gray.12",  # High contrast text
    border_radius="var(--radius-3)"  # Uses theme radius
)
```

---

## State Architecture (Advanced)

### State Scope Decision Tree

**Use GLOBAL state when**:
- Data shared across multiple pages (user auth, shopping cart)
- Data persists during navigation
- Multiple components need to read/write the same data

**Use LOCAL state when**:
- Data only relevant to one page (form inputs, modal visibility)
- Data should reset when leaving the page
- Temporary UI state

```python
# Global state (module level)
class AuthState(rx.State):
    """Accessible from anywhere in the app"""
    username: str = ""
    is_logged_in: bool = False
    
    def login(self, username: str):
        self.username = username
        self.is_logged_in = True

# Local state (inside page function)
def contact_page():
    class FormState(rx.State):
        """Only exists for this page, resets on navigation"""
        name: str = ""
        email: str = ""
        message: str = ""
        submitted: bool = False
        
        def submit(self):
            # Process form
            self.submitted = True
    
    return rx.vstack(
        rx.input(value=FormState.name, on_change=FormState.set_name),
        # ... rest of form
    )
```

### Computed Properties (@rx.var)

**CRITICAL OPTIMIZATION**: Use computed vars instead of storing derived data.

```python
class ShoppingCartState(rx.State):
    items: list[dict] = []  # Only store source data
    
    # ✅ CORRECT - Computed automatically
    @rx.var
    def total_price(self) -> float:
        return sum(item["price"] * item["quantity"] for item in self.items)
    
    @rx.var
    def item_count(self) -> int:
        return sum(item["quantity"] for item in self.items)
    
    @rx.var
    def is_empty(self) -> bool:
        return len(self.items) == 0
    
    # ❌ WRONG - Don't store derived data manually
    # total_price: float = 0.0
    # item_count: int = 0
```

**Computed Var with Dependencies**:
```python
class FilterState(rx.State):
    all_products: list[dict] = []
    search_query: str = ""
    category_filter: str = "all"
    min_price: float = 0.0
    
    @rx.var
    def filtered_products(self) -> list[dict]:
        """Automatically recomputes when any dependency changes"""
        results = self.all_products
        
        if self.search_query:
            results = [p for p in results if self.search_query.lower() in p["name"].lower()]
        
        if self.category_filter != "all":
            results = [p for p in results if p["category"] == self.category_filter]
        
        if self.min_price > 0:
            results = [p for p in results if p["price"] >= self.min_price]
        
        return results
```

### State Inheritance Pattern

```python
class BaseState(rx.State):
    """Shared base functionality"""
    loading: bool = False
    error: str = ""
    
    def set_error(self, msg: str):
        self.error = msg
        self.loading = False
    
    def clear_error(self):
        self.error = ""

class UserState(BaseState):
    """Inherits loading and error handling"""
    users: list[dict] = []
    
    async def load_users(self):
        self.loading = True
        self.clear_error()
        try:
            # ... fetch users
            pass
        except Exception as e:
            self.set_error(str(e))
        finally:
            self.loading = False

class ProductState(BaseState):
    """Also inherits same patterns"""
    products: list[dict] = []
    
    async def load_products(self):
        # Same pattern as UserState
        pass
```

---

## Routing & Navigation

### Page Registration Patterns

```python
# Simple static page
def about_page():
    return rx.center(rx.heading("About Us"))

app.add_page(about_page, route="/about", title="About - My App")

# Dynamic route with parameter
def user_profile(username: str):  # Parameter name must match route
    return rx.vstack(
        rx.heading(f"Profile: {username}"),
        rx.text(f"User data for {username}")
    )

app.add_page(user_profile, route="/users/[username]")

# Multiple dynamic parameters
def blog_post(year: str, month: str, slug: str):
    return rx.box(
        rx.heading(f"Post: {slug}"),
        rx.text(f"Published: {year}-{month}")
    )

app.add_page(blog_post, route="/blog/[year]/[month]/[slug]")

# Catch-all route
def docs_page(path: str):  # path will be "guide/intro" for /docs/guide/intro
    return rx.text(f"Documentation: {path}")

app.add_page(docs_page, route="/docs/[...path]")
```

### Navigation Methods

```python
class NavigationState(rx.State):
    def go_to_dashboard(self):
        return rx.redirect("/dashboard")
    
    def go_back(self):
        return rx.redirect_back()  # Previous page
    
    def go_to_user(self, user_id: str):
        return rx.redirect(f"/users/{user_id}")
    
    def external_link(self):
        return rx.redirect("https://example.com", external=True)

# In components
rx.button("Dashboard", on_click=NavigationState.go_to_dashboard)
rx.link("About", href="/about")  # Client-side navigation
```

### Route Guards Pattern

```python
def protected_page():
    """Pattern: Check auth and redirect at page entry"""
    if not AuthState.is_logged_in:
        return rx.redirect("/login")
    
    return rx.vstack(
        rx.heading("Protected Content"),
        # ... authenticated content
    )

def admin_page():
    """Pattern: Multi-level access control"""
    if not AuthState.is_logged_in:
        return rx.redirect("/login")
    
    if AuthState.role != "admin":
        return rx.redirect("/403")  # Forbidden
    
    return rx.vstack(
        rx.heading("Admin Panel"),
        # ... admin content
    )
```

---

## Database & API Integration

### Database Pattern with SQLModel

```python
from sqlmodel import SQLModel, Field, create_engine, Session
import asyncio

# Model definition
class Todo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

# Setup
engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# State with CRUD operations
class TodoState(rx.State):
    todos: list[dict] = []
    loading: bool = False
    
    def _load_todos_sync(self) -> list[dict]:
        """Sync helper - never call directly from UI"""
        with Session(engine) as session:
            results = session.query(Todo).all()
            return [
                {"id": t.id, "title": t.title, "completed": t.completed}
                for t in results
            ]
    
    async def load_todos(self):
        """Async wrapper - call this from UI"""
        self.loading = True
        try:
            self.todos = await asyncio.to_thread(self._load_todos_sync)
        finally:
            self.loading = False
    
    def _add_todo_sync(self, title: str):
        with Session(engine) as session:
            todo = Todo(title=title)
            session.add(todo)
            session.commit()
    
    async def add_todo(self, title: str):
        await asyncio.to_thread(self._add_todo_sync, title)
        await self.load_todos()  # Refresh after create
    
    def _update_todo_sync(self, todo_id: int, completed: bool):
        with Session(engine) as session:
            todo = session.get(Todo, todo_id)
            if todo:
                todo.completed = completed
                session.commit()
    
    async def toggle_todo(self, todo_id: int, completed: bool):
        await asyncio.to_thread(self._update_todo_sync, todo_id, completed)
        await self.load_todos()  # Refresh after update
    
    def _delete_todo_sync(self, todo_id: int):
        with Session(engine) as session:
            todo = session.get(Todo, todo_id)
            if todo:
                session.delete(todo)
                session.commit()
    
    async def delete_todo(self, todo_id: int):
        await asyncio.to_thread(self._delete_todo_sync, todo_id)
        await self.load_todos()  # Refresh after delete
```

### API Integration Pattern

```python
import httpx

class APIState(rx.State):
    data: dict | None = None
    loading: bool = False
    error: str = ""
    
    async def fetch_data(self, endpoint: str):
        if self.loading:
            return
        
        self.loading = True
        self.error = ""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.example.com/{endpoint}",
                    headers={"Authorization": f"Bearer {os.getenv('API_KEY')}"}
                )
                response.raise_for_status()
                self.data = response.json()
        except httpx.HTTPError as e:
            self.error = f"HTTP error: {e}"
        except Exception as e:
            self.error = f"Error: {e}"
        finally:
            self.loading = False
    
    async def post_data(self, payload: dict):
        self.loading = True
        self.error = ""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.example.com/submit",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return rx.toast.success("Data submitted!")
        except Exception as e:
            self.error = str(e)
            return rx.toast.error(f"Failed: {e}")
        finally:
            self.loading = False
```

### Service Layer Pattern (Recommended for Large Apps)

```python
# services/todo_service.py
class TodoService:
    @staticmethod
    def get_all_todos() -> list[Todo]:
        with Session(engine) as session:
            return session.query(Todo).all()
    
    @staticmethod
    def create_todo(title: str) -> Todo:
        with Session(engine) as session:
            todo = Todo(title=title)
            session.add(todo)
            session.commit()
            session.refresh(todo)
            return todo
    
    @staticmethod
    def update_todo(todo_id: int, **updates) -> Todo | None:
        with Session(engine) as session:
            todo = session.get(Todo, todo_id)
            if todo:
                for key, value in updates.items():
                    setattr(todo, key, value)
                session.commit()
                session.refresh(todo)
            return todo
    
    @staticmethod
    def delete_todo(todo_id: int) -> bool:
        with Session(engine) as session:
            todo = session.get(Todo, todo_id)
            if todo:
                session.delete(todo)
                session.commit()
                return True
            return False

# state/todo_state.py
class TodoState(rx.State):
    todos: list[dict] = []
    
    async def load_todos(self):
        results = await asyncio.to_thread(TodoService.get_all_todos)
        self.todos = [{"id": t.id, "title": t.title} for t in results]
    
    async def add_todo(self, title: str):
        await asyncio.to_thread(TodoService.create_todo, title)
        await self.load_todos()
```

---

## Forms & Validation

### Form State Pattern

```python
class ContactFormState(rx.State):
    # Form fields
    name: str = ""
    email: str = ""
    message: str = ""
    
    # Validation errors
    name_error: str = ""
    email_error: str = ""
    message_error: str = ""
    
    # Submission state
    is_submitting: bool = False
    submit_success: bool = False
    submit_error: str = ""
    
    def validate_name(self) -> bool:
        if len(self.name.strip()) < 2:
            self.name_error = "Name must be at least 2 characters"
            return False
        self.name_error = ""
        return True
    
    def validate_email(self) -> bool:
        if "@" not in self.email or "." not in self.email:
            self.email_error = "Please enter a valid email"
            return False
        self.email_error = ""
        return True
    
    def validate_message(self) -> bool:
        if len(self.message.strip()) < 10:
            self.message_error = "Message must be at least 10 characters"
            return False
        self.message_error = ""
        return True
    
    async def submit(self):
        # Prevent double submission
        if self.is_submitting:
            return
        
        # Validate all fields
        valid_name = self.validate_name()
        valid_email = self.validate_email()
        valid_message = self.validate_message()
        
        if not (valid_name and valid_email and valid_message):
            return
        
        # Submit
        self.is_submitting = True
        self.submit_error = ""
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://api.example.com/contact",
                    json={
                        "name": self.name,
                        "email": self.email,
                        "message": self.message
                    }
                )
            self.submit_success = True
            # Clear form
            self.name = ""
            self.email = ""
            self.message = ""
            return rx.toast.success("Message sent!")
        except Exception as e:
            self.submit_error = str(e)
            return rx.toast.error("Failed to send message")
        finally:
            self.is_submitting = False

# UI Component
def contact_form():
    return rx.vstack(
        rx.input(
            placeholder="Name",
            value=ContactFormState.name,
            on_change=ContactFormState.set_name,
            on_blur=ContactFormState.validate_name
        ),
        rx.cond(
            ContactFormState.name_error != "",
            rx.text(ContactFormState.name_error, color="red", size="sm")
        ),
        
        rx.input(
            placeholder="Email",
            value=ContactFormState.email,
            on_change=ContactFormState.set_email,
            on_blur=ContactFormState.validate_email
        ),
        rx.cond(
            ContactFormState.email_error != "",
            rx.text(ContactFormState.email_error, color="red", size="sm")
        ),
        
        rx.text_area(
            placeholder="Message",
            value=ContactFormState.message,
            on_change=ContactFormState.set_message,
            on_blur=ContactFormState.validate_message
        ),
        rx.cond(
            ContactFormState.message_error != "",
            rx.text(ContactFormState.message_error, color="red", size="sm")
        ),
        
        rx.button(
            "Send Message",
            on_click=ContactFormState.submit,
            disabled=ContactFormState.is_submitting,
            loading=ContactFormState.is_submitting
        ),
        
        spacing="1rem",
        width="100%"
    )
```

---

## Authentication & Security

### Password Hashing (CRITICAL)

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthState(rx.State):
    username: str = ""
    is_logged_in: bool = False
    user_id: int | None = None
    
    def _register_user_sync(self, username: str, password: str) -> bool:
        """Never store plain passwords!"""
        with Session(engine) as session:
            # Check if user exists
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return False
            
            # Hash password
            hashed = pwd_context.hash(password)
            
            # Store user
            user = User(username=username, password_hash=hashed)
            session.add(user)
            session.commit()
            return True
    
    async def register(self, username: str, password: str):
        success = await asyncio.to_thread(
            self._register_user_sync, username, password
        )
        if success:
            return rx.toast.success("Registration successful!")
        return rx.toast.error("Username already exists")
    
    def _verify_login_sync(self, username: str, password: str) -> dict | None:
        with Session(engine) as session:
            user = session.query(User).filter_by(username=username).first()
            if user and pwd_context.verify(password, user.password_hash):
                return {"id": user.id, "username": user.username}
            return None
    
    async def login(self, username: str, password: str):
        user_data = await asyncio.to_thread(
            self._verify_login_sync, username, password
        )
        if user_data:
            self.username = user_data["username"]
            self.user_id = user_data["id"]
            self.is_logged_in = True
            return rx.redirect("/dashboard")
        return rx.toast.error("Invalid credentials")
    
    def logout(self):
        self.username = ""
        self.user_id = None
        self.is_logged_in = False
        return rx.redirect("/")
```

### Environment Variables (Security)

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

class APIState(rx.State):
    def fetch_data(self):
        # ✅ CORRECT - Secrets stay on server
        api_key = os.getenv("API_KEY")
        db_password = os.getenv("DB_PASSWORD")
        
        # Use secrets in server-side operations
        # Never assign to state variables!
        
    # ❌ WRONG - Don't do this!
    # api_key: str = os.getenv("API_KEY")  # This would be sent to client!
```

### Input Sanitization (XSS Prevention)

```python
import html
import bleach

class CommentState(rx.State):
    comments: list[dict] = []
    
    async def add_comment(self, text: str):
        # Sanitize HTML to prevent XSS
        clean_text = bleach.clean(
            text,
            tags=["b", "i", "u", "p", "br"],  # Allow only safe tags
            strip=True
        )
        
        # Or escape all HTML
        safe_text = html.escape(text)
        
        # Store sanitized version
        await self._store_comment_sync(safe_text)

# In UI, if rendering user HTML:
rx.html(CommentState.comment_text)  # Only use with sanitized content!
```

---

## Advanced UI Patterns

### Modal/Dialog Pattern

```python
class ModalState(rx.State):
    show_modal: bool = False
    modal_data: dict | None = None
    
    def open_modal(self, data: dict):
        self.modal_data = data
        self.show_modal = True
    
    def close_modal(self):
        self.show_modal = False
        self.modal_data = None

def modal_dialog():
    return rx.cond(
        ModalState.show_modal,
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Confirmation"),
                rx.dialog.description(
                    f"Process item: {ModalState.modal_data}"
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancel", on_click=ModalState.close_modal)
                    ),
                    rx.button("Confirm", on_click=ModalState.process),
                    spacing="1rem"
                ),
                padding="1rem"
            ),
            open=ModalState.show_modal
        )
    )
```

### File Upload Pattern

```python
class FileUploadState(rx.State):
    uploading: bool = False
    upload_progress: int = 0
    uploaded_file_url: str = ""
    
    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            return rx.toast.error("No file selected")
        
        file = files[0]
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "application/pdf"]
        if file.content_type not in allowed_types:
            return rx.toast.error("Invalid file type")
        
        # Validate file size (e.g., max 5MB)
        max_size = 5 * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_size:
            return rx.toast.error("File too large (max 5MB)")
        
        self.uploading = True
        
        try:
            # Save file locally
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            self.uploaded_file_url = f"/{file_path}"
            return rx.toast.success("File uploaded!")
        except Exception as e:
            return rx.toast.error(f"Upload failed: {e}")
        finally:
            self.uploading = False

# UI
rx.upload(
    rx.button("Select File", disabled=FileUploadState.uploading),
    on_upload=FileUploadState.handle_upload,
    multiple=False
)
```

### Toast Notifications

```python
class NotificationState(rx.State):
    async def save_data(self):
        try:
            # ... save logic
            return rx.toast.success(
                "Data saved successfully!",
                duration=3000  # milliseconds
            )
        except Exception as e:
            return rx.toast.error(
                f"Save failed: {e}",
                duration=5000
            )
    
    def show_info(self):
        return rx.toast.info("Processing in background...")
    
    def show_warning(self):
        return rx.toast.warning("Your session will expire soon")
```

### Dynamic Charts with Recharts

```python
class ChartState(rx.State):
    chart_data: list[dict] = [
        {"month": "Jan", "sales": 4000, "expenses": 2400},
        {"month": "Feb", "sales": 3000, "expenses": 1398},
        {"month": "Mar", "sales": 2000, "expenses": 9800},
    ]
    
    def update_data(self, new_data: list[dict]):
        self.chart_data = new_data  # Chart auto-updates

def sales_chart():
    return rx.recharts.line_chart(
        rx.recharts.line(data_key="sales", stroke="#8884d8"),
        rx.recharts.line(data_key="expenses", stroke="#82ca9d"),
        rx.recharts.x_axis(data_key="month"),
        rx.recharts.y_axis(),
        rx.recharts.legend(),
        data=ChartState.chart_data,  # Bind to state
        width="100%",
        height=300
    )
```

---

## Real-Time Communication

### WebSocket Broadcasting Pattern

```python
class ChatState(rx.State):
    messages: list[dict] = []
    username: str = ""
    
    async def send_message(self, text: str):
        if not text.strip():
            return
        
        message = {
            "username": self.username,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to local state
        self.messages.append(message)
        self.messages = list(self.messages)
        
        # Broadcast to all connected clients
        # This triggers reload_messages() on all other clients
        await self.broadcast("reload_messages")
    
    async def reload_messages(self):
        """Called on all clients when broadcast is received"""
        # Fetch latest messages from database
        messages = await asyncio.to_thread(self._fetch_messages_sync)
        self.messages = messages

# UI updates automatically for all users
def chat_interface():
    return rx.vstack(
        rx.foreach(
            ChatState.messages,
            lambda msg: rx.box(
                rx.text(msg["username"], font_weight="bold"),
                rx.text(msg["text"]),
                rx.text(msg["timestamp"], size="sm", color="gray")
            )
        ),
        rx.input(
            placeholder="Type a message...",
            on_submit=ChatState.send_message
        )
    )
```

### Event Streaming Pattern

```python
class StreamState(rx.State):
    stream_data: str = ""
    is_streaming: bool = False
    
    async def start_stream(self):
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.stream_data = ""
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", "https://api.example.com/stream") as response:
                    async for chunk in response.aiter_text():
                        self.stream_data += chunk
                        yield  # Update UI incrementally
        finally:
            self.is_streaming = False
```

---

## Performance Optimization

### Computed Vars (Most Important)

```python
# ❌ BAD - Storing redundant data
class TaskStateBad(rx.State):
    all_tasks: list[dict] = []
    completed_tasks: list[dict] = []  # Redundant!
    pending_tasks: list[dict] = []    # Redundant!
    completed_count: int = 0           # Redundant!
    
    def add_task(self, task: dict):
        self.all_tasks.append(task)
        # Now you have to manually update all derived data
        self._recalculate_everything()  # Error-prone!

# ✅ GOOD - Computed properties
class TaskStateGood(rx.State):
    all_tasks: list[dict] = []  # Only source data
    
    @rx.var
    def completed_tasks(self) -> list[dict]:
        return [t for t in self.all_tasks if t["completed"]]
    
    @rx.var
    def pending_tasks(self) -> list[dict]:
        return [t for t in self.all_tasks if not t["completed"]]
    
    @rx.var
    def completed_count(self) -> int:
        return len(self.completed_tasks)
    
    @rx.var
    def completion_percentage(self) -> float:
        if not self.all_tasks:
            return 0.0
        return (self.completed_count / len(self.all_tasks)) * 100
    
    def add_task(self, task: dict):
        self.all_tasks.append(task)
        self.all_tasks = list(self.all_tasks)
        # All computed properties update automatically!
```

### Pagination Pattern

```python
class PaginatedState(rx.State):
    all_items: list[dict] = []  # Full dataset
    page: int = 1
    items_per_page: int = 20
    
    @rx.var
    def total_pages(self) -> int:
        return (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
    
    @rx.var
    def current_page_items(self) -> list[dict]:
        """Only compute the items for current page"""
        start = (self.page - 1) * self.items_per_page
        end = start + self.items_per_page
        return self.all_items[start:end]
    
    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
    
    def prev_page(self):
        if self.page > 1:
            self.page -= 1
    
    def go_to_page(self, page_num: int):
        if 1 <= page_num <= self.total_pages:
            self.page = page_num

# UI only renders current page
def paginated_list():
    return rx.vstack(
        rx.foreach(
            PaginatedState.current_page_items,  # Only 20 items rendered
            lambda item: item_card(item)
        ),
        rx.hstack(
            rx.button("Previous", on_click=PaginatedState.prev_page),
            rx.text(f"Page {PaginatedState.page} of {PaginatedState.total_pages}"),
            rx.button("Next", on_click=PaginatedState.next_page)
        )
    )
```

### Lazy Loading Pattern

```python
class LazyLoadState(rx.State):
    visible_items: list[dict] = []
    offset: int = 0
    batch_size: int = 50
    has_more: bool = True
    loading: bool = False
    
    async def load_more(self):
        if self.loading or not self.has_more:
            return
        
        self.loading = True
        try:
            new_items = await asyncio.to_thread(
                self._fetch_batch_sync,
                self.offset,
                self.batch_size
            )
            
            if len(new_items) < self.batch_size:
                self.has_more = False
            
            self.visible_items.extend(new_items)
            self.visible_items = list(self.visible_items)
            self.offset += len(new_items)
        finally:
            self.loading = False

# UI with infinite scroll
def lazy_list():
    return rx.vstack(
        rx.foreach(
            LazyLoadState.visible_items,
            lambda item: item_card(item)
        ),
        rx.cond(
            LazyLoadState.has_more,
            rx.button(
                "Load More",
                on_click=LazyLoadState.load_more,
                loading=LazyLoadState.loading
            )
        )
    )
```

### Debouncing Pattern (Search)

```python
import asyncio

class SearchState(rx.State):
    search_query: str = ""
    search_results: list[dict] = []
    is_searching: bool = False
    _search_task: asyncio.Task | None = None
    
    def update_search_query(self, query: str):
        """Called on every keystroke"""
        self.search_query = query
        
        # Cancel previous search
        if self._search_task and not self._search_task.done():
            self._search_task.cancel()
        
        # Schedule new search with delay
        self._search_task = asyncio.create_task(self._debounced_search())
    
    async def _debounced_search(self):
        """Waits 300ms before actually searching"""
        await asyncio.sleep(0.3)  # Debounce delay
        
        if not self.search_query.strip():
            self.search_results = []
            return
        
        self.is_searching = True
        try:
            results = await asyncio.to_thread(
                self._search_database_sync,
                self.search_query
            )
            self.search_results = results
        finally:
            self.is_searching = False

# UI
rx.input(
    placeholder="Search...",
    value=SearchState.search_query,
    on_change=SearchState.update_search_query  # Triggers on every keystroke
)
```

---

## Testing Patterns

### Unit Testing State Methods

```python
import pytest
from unittest.mock import patch, MagicMock

def test_add_task():
    """Test adding a task updates state correctly"""
    state = TaskState()
    
    state.add_task("Buy groceries")
    
    assert len(state.tasks) == 1
    assert state.tasks[0]["title"] == "Buy groceries"
    assert state.tasks[0]["completed"] == False

def test_toggle_task():
    """Test toggling task completion"""
    state = TaskState()
    state.tasks = [{"id": 1, "title": "Test", "completed": False}]
    
    state.toggle_task(1)
    
    assert state.tasks[0]["completed"] == True

@pytest.mark.asyncio
async def test_load_tasks_from_api():
    """Test async API call with mocking"""
    state = APIState()
    
    # Mock the HTTP client
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {"tasks": [{"id": 1, "title": "Test"}]}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        await state.load_tasks()
        
        assert state.tasks == [{"id": 1, "title": "Test"}]
        assert state.loading == False

def test_computed_var():
    """Test computed properties"""
    state = TaskState()
    state.all_tasks = [
        {"completed": True},
        {"completed": False},
        {"completed": True}
    ]
    
    # Computed var should calculate correctly
    assert state.completed_count == 2
    assert state.completion_percentage == pytest.approx(66.67, rel=0.01)
```

### End-to-End Testing with Playwright

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def reflex_app():
    """Start Reflex app for testing"""
    import subprocess
    import time
    
    process = subprocess.Popen(["reflex", "run", "--port", "3001"])
    time.sleep(5)  # Wait for app to start
    
    yield "http://localhost:3001"
    
    process.terminate()
    process.wait()

def test_todo_app_flow(page: Page, reflex_app):
    """Test complete user flow"""
    page.goto(reflex_app)
    
    # Check page loaded
    expect(page.locator("h1")).to_contain_text("Todo App")
    
    # Add a task
    page.fill('input[placeholder="Add a task"]', "Buy milk")
    page.click('button:has-text("Add")')
    
    # Verify task appears
    expect(page.locator("text=Buy milk")).to_be_visible()
    
    # Complete the task
    page.click('input[type="checkbox"]')
    
    # Verify task is marked complete
    expect(page.locator(".completed-task")).to_contain_text("Buy milk")

def test_login_flow(page: Page, reflex_app):
    """Test authentication"""
    page.goto(f"{reflex_app}/login")
    
    # Fill login form
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "testpass123")
    page.click('button[type="submit"]')
    
    # Should redirect to dashboard
    expect(page).to_have_url(f"{reflex_app}/dashboard")
    expect(page.locator("text=Welcome, testuser")).to_be_visible()
```

---

## Deployment Patterns

### Production Configuration

```python
# config.py
import os

class Config:
    # Environment
    ENV = os.getenv("REFLEX_ENV", "development")
    IS_PRODUCTION = ENV == "production"
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///reflex.db" if not IS_PRODUCTION else None
    )
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if IS_PRODUCTION and not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in production")
    
    # API
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # Features
    ENABLE_ANALYTICS = IS_PRODUCTION
    DEBUG = not IS_PRODUCTION

# Use in app
from config import Config

class AppState(rx.State):
    def log_event(self, event: str):
        if Config.ENABLE_ANALYTICS:
            # Send to analytics service
            pass
```

### Docker Setup (Multi-Stage)

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Node.js (required for Reflex)
RUN apt-get update && apt-get install -y nodejs npm curl

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Export production build
RUN reflex export --no-zip

# ---
# Production stage (smaller image)
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built assets from builder
COPY --from=builder /app/.web/_static /app/.web/_static
COPY --from=builder /app/*.py /app/
COPY --from=builder /app/assets /app/assets

# Set production environment
ENV REFLEX_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run production server
CMD ["reflex", "run", "--env", "production", "--loglevel", "info"]
```

### Health Check Endpoint

```python
# Add to your main app file

def health_check():
    """Simple health check for load balancers"""
    return rx.box(
        rx.text("OK"),
        display="none"
    )

app.add_page(health_check, route="/health")

# Or create an API endpoint
@app.api.get("/api/health")
async def api_health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
```

### Environment Variables (.env)

```bash
# .env (DO NOT COMMIT TO GIT!)
REFLEX_ENV=production
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key-here
API_KEY=your-api-key-here

# Redis (if using)
REDIS_URL=redis://localhost:6379

# External services
STRIPE_SECRET_KEY=sk_live_...
SENDGRID_API_KEY=SG...
```

---

## Error Handling Patterns

### Global Error Handler

```python
class ErrorState(rx.State):
    error_message: str = ""
    error_details: str = ""
    show_error: bool = False
    
    def handle_error(self, error: Exception):
        """Centralized error handling"""
        self.error_message = str(error)
        self.error_details = traceback.format_exc() if Config.DEBUG else ""
        self.show_error = True
        
        # Log error (send to logging service in production)
        logging.error(f"Error occurred: {error}", exc_info=True)
        
        return rx.toast.error("An error occurred")
    
    def clear_error(self):
        self.error_message = ""
        self.error_details = ""
        self.show_error = False

# Use in other states
class DataState(rx.State):
    async def fetch_data(self):
        try:
            # ... fetch logic
            pass
        except Exception as e:
            return ErrorState.handle_error(e)
```

### Retry Pattern

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryState(rx.State):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def fetch_with_retry(self):
        """Automatically retries on failure"""
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()
    
    async def load_data(self):
        try:
            data = await self.fetch_with_retry()
            self.data = data
        except Exception as e:
            return rx.toast.error(f"Failed after 3 attempts: {e}")
```

---

## Code Organization Best Practices

### Project Structure

```
my_app/
├── my_app/
│   ├── __init__.py
│   ├── my_app.py          # Main app file
│   ├── config.py           # Configuration
│   ├── models/            # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── post.py
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── post_service.py
│   ├── states/            # Reflex states
│   │   ├── __init__.py
│   │   ├── auth_state.py
│   │   ├── blog_state.py
│   │   └── base_state.py
│   ├── components/        # Reusable UI components
│   │   ├── __init__.py
│   │   ├── header.py
│   │   ├── footer.py
│   │   └── card.py
│   └── pages/            # Page definitions
│       ├── __init__.py
│       ├── index.py
│       ├── blog.py
│       └── dashboard.py
├── assets/               # Static files
├── tests/               # Test files
├── .env                 # Environment variables (gitignored)
├── requirements.txt     
└── Dockerfile
```

### Import Organization

```python
# Standard library
import os
import asyncio
from datetime import datetime

# Third-party
import reflex as rx
from sqlmodel import SQLModel, Field, Session
import httpx

# Local
from .models import User, Post
from .services import UserService, PostService
from .states.base_state import BaseState
```

### Constants and Configuration

```python
# constants.py
# Define magic strings and numbers in one place

# UI
DEFAULT_PAGE_SIZE = 20
MAX_FILE_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]

# Business logic
MIN_PASSWORD_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT_MINUTES = 30

# API
API_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
RATE_LIMIT_PER_MINUTE = 60
```

---

## Instrument your backend: structured logs

Prints are fine, but structured logs are better. Add a small decorator that logs method name, arguments, duration, and what changed. Keep it framework-agnostic so you can reuse it across projects.

```python
# debug_tools.py
from functools import wraps
from time import perf_counter
import logging
import json
from typing import Callable

# Set up basic logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reflex.debug")

def trace_state(method: Callable):
    """Log entry/exit and duration for a state method."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        start = perf_counter()
        
        # --- CORRECTED LOGGING ---
        # Formats args and kwargs for a readable log
        args_repr = ", ".join(repr(a) for a in args)
        kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        separator = ", " if args and kwargs else ""
        log.info("TRACE %s(%s%s%s)", method.__name__, args_repr, separator, kwargs_repr)
        # --- END CORRECTION ---

        before = snapshot_state(self)
        try:
            # This part was correct: execute the original method
            return method(self, *args, **kwargs)
        finally:
            # This part was also correct: log changes after execution
            after = snapshot_state(self)
            changed = diff_snapshots(before, after)
            elapsed = (perf_counter() - start) * 1000
            log.info(
                "TRACE %s | %0.2f ms | changed=%s",
                method.__name__,
                elapsed,
                json.dumps(changed),
            )
            
    # This return was correct, it returns the decorated function
    return wrapper

def snapshot_state(state_obj):
    """Small, conservative snapshot—list only primitive fields to avoid huge logs"""
    out = {}
    
    # --- CORRECTED FUNCTION BODY ---
    # Use state_obj.__dict__ to iterate over attributes
    for k, v in state_obj.__dict__.items():
        # Corrected: k.startswith("_")
        if k.startswith("_"):
            continue
        
        # Corrected: Indentation for out[k] = v
        if isinstance(v, (int, float, str, bool, type(None))):
            out[k] = v
        
        # Corrected: Readability
        elif isinstance(v, (list, tuple)):
            # Check if all items are primitive before slicing
            if all(isinstance(x, (int, float, str, bool, type(None))) for x in v[:10]):
                out[k] = list(v[:10])  # avoid huge payloads
        
        elif isinstance(v, dict):
            # include first few primitive items only
            items = []
            for i, (kk, vv) in enumerate(v.items()):
                # Corrected: Indentation for break
                if i >= 10:
                    break
                if isinstance(vv, (int, float, str, bool, type(None))):
                    items.append((str(kk), vv)) # Ensure key is string
            out[k] = dict(items)
            
    # Corrected: Unindented return to be outside the loop
    return out
    # --- END CORRECTION ---

def diff_snapshots(a, b):
    """(This function was correct in the original)"""
    changed = {}
    all_keys = set(a.keys()) | set(b.keys())
    for k in all_keys:
        if a.get(k) != b.get(k):
            changed[k] = {"from": a.get(k), "to": b.get(k)}
    return changed
```

And then use it on any state method that should mutate fields:

```python
# state.py
import reflex as rx
from .debug_tools import trace_state

class ProfileState(rx.State):
    """A state class to demonstrate tracing."""
    
    # --- ATTRIBUTES ---
    name: str = ""
    saving: bool = False
    
    # Corrected: This attribute is now correctly indented
    # to be part of the ProfileState class.
    error: str | None = None

    # --- METHODS ---
    
    @trace_state
    def set_name(self, value: str):
        """Sets the user's name."""
        self.name = value

    @trace_state
    def save(self):
        """Saves the profile, demonstrating tracing on a method with logic."""
        self.error = None
        self.saving = True
        try:
            # Simulate I/O work or validation
            if not self.name.strip():
                raise ValueError("Name is required")
            # If successful, do nothing (just pretend)
            
        except Exception as e:
            # If an error occurs, log it to the state
            self.error = str(e)
        finally:
            # Always set saving to False when done
            self.saving = False
```



---

## Quick Reference: Common Issues

### Issue: State not updating UI

```python
# ❌ WRONG
def add_item(self, item):
    self.items.append(item)  # May not trigger update

# ✅ CORRECT
def add_item(self, item):
    self.items.append(item)
    self.items = list(self.items)  # Force update
```

### Issue: Blocking async operations

```python
# ❌ WRONG - Blocks event loop
async def load_data(self):
    data = blocking_database_call()  # Freezes app!

# ✅ CORRECT - Use asyncio.to_thread
async def load_data(self):
    data = await asyncio.to_thread(blocking_database_call)
```

### Issue: Secrets exposed to client

```python
# ❌ WRONG - API key sent to browser!
class State(rx.State):
    api_key: str = os.getenv("API_KEY")

# ✅ CORRECT - Keep secrets in methods
class State(rx.State):
    async def fetch_data(self):
        api_key = os.getenv("API_KEY")  # Stays on server
        # Use api_key here
```

### Issue: Race conditions in async

```python
# ❌ WRONG - Multiple simultaneous requests
async def fetch(self):
    data = await api_call()  # Can be called multiple times

# ✅ CORRECT - Use loading flag
async def fetch(self):
    if self.loading:
        return  # Prevent duplicate requests
    self.loading = True
    try:
        data = await api_call()
    finally:
        self.loading = False
```

### Issue: Form submissions not working

```python
# ❌ WRONG - Using HTML form tags in React
def my_form():
    return rx.box(
        rx.html("<form>...</form>")  # Doesn't work!
    )

# ✅ CORRECT - Use event handlers
def my_form():
    return rx.vstack(
        rx.input(value=State.name, on_change=State.set_name),
        rx.button("Submit", on_click=State.submit)  # Use on_click
    )
```

---

## Agent-Specific Guidelines

### When generating Reflex code:

1. **Always include proper type hints** on state variables
2. **Use computed vars (@rx.var)** instead of storing derived data
3. **Wrap blocking I/O** in `asyncio.to_thread()`
4. **Include loading flags** for any async operations
5. **Add defensive reassignment** when modifying lists/dicts
6. **Never hardcode secrets** - use environment variables
7. **Validate user input** before processing
8. **Use try/except/finally** for error handling
9. **Return feedback** (rx.toast, rx.redirect) from state methods
10. **Keep components small** and reusable

### Code generation checklist:

- [ ] All state vars have type annotations
- [ ] Async operations use loading flags
- [ ] Blocking calls wrapped in asyncio.to_thread
- [ ] Computed properties use @rx.var
- [ ] Error handling with try/except
- [ ] User feedback (toasts/redirects)
- [ ] Input validation and sanitization
- [ ] No secrets in state variables
- [ ] Defensive container reassignment
- [ ] Components are composable and reusable