# PDFQuill Marketplace - Deployment Guide (Render.com)

This guide provides instructions for deploying the PDFQuill Marketplace application to Render.com.

## Prerequisites

1.  **Render Account:** You'll need an account on [Render.com](https://render.com/).
2.  **Git Repository:** Your application code should be in a Git repository (e.g., GitHub, GitLab, Bitbucket) linked to your Render account.
3.  **Paystack Account:** For payment processing, you'll need a Paystack account with API keys (secret and public).

## Deployment Steps

This application is configured for deployment using Docker and includes a PostgreSQL database.

### 1. Using `render.yaml` (Recommended)

The easiest way to deploy is by using the `render.yaml` file located in the root of this repository. Render can automatically detect and configure your services based on this file.

1.  **Create a New Blueprint Instance on Render:**
    *   Go to your Render Dashboard.
    *   Click "New" -> "Blueprint".
    *   Connect your Git repository where this project resides.
    *   Render will detect the `render.yaml` file. Review the proposed services (a web service for the Flask app and a PostgreSQL database service).
    *   Click "Create Resources" (or similar, the button text might vary).

2.  **Configure Environment Variables:**
    *   After the services are created (or during the creation process if prompted), navigate to the "Environment" section for your **web service** (`pdfquill-app` or the name you chose).
    *   The `render.yaml` file specifies several environment variables. Some, like `DATABASE_URL` and `SECRET_KEY` (if `generateValue: true` was used), will be automatically configured by Render.
    *   You **MUST** manually add and set the following sensitive environment variables:
        *   `PAYSTACK_SECRET_KEY`: Your Paystack live or test secret key.
        *   `PAYSTACK_PUBLIC_KEY`: Your Paystack live or test public key.
        *   `MAIL_SERVER`: e.g., `smtp.gmail.com` or your mail provider's SMTP server.
        *   `MAIL_PORT`: e.g., `587` (for TLS) or `465` (for SSL).
        *   `MAIL_USE_TLS`: `true` or `false`.
        *   `MAIL_USERNAME`: Your email account username.
        *   `MAIL_PASSWORD`: Your email account password or app-specific password.
        *   `MAIL_DEFAULT_SENDER`: e.g., `"PDFQuill App" <noreply@yourdomain.com>`
        *   `ADMIN_EMAIL`: The email address for receiving admin notifications from the app.
    *   You can also override other variables like `FLASK_ENV` (though it defaults to `production` in `render.yaml` and `Dockerfile`).

3.  **Initial Migration and Admin User Creation (First Deploy):**
    *   Once the application is deployed and running, you'll likely need to initialize the database schema and create an initial admin user.
    *   Render provides an SSH shell into your running service instance (for web services on paid plans) or you can use the "Shell" tab on the service page (sometimes available on free plans, or use one-off jobs).
    *   **Database Migrations:** If you implement database migrations (e.g., with Flask-Migrate, which is not explicitly part of this project's current setup but highly recommended for production), you would run your migration commands here:
        ```bash
        flask db upgrade
        ```
        (Assuming Flask-Migrate is set up with `flask db` commands. If not, `db.create_all()` is called on app start, which is okay for initial setup but less flexible for schema changes).
    *   **Creating an Admin User:** You might need to run a script or use the Flask shell to create the first admin user if one isn't seeded automatically.
        ```bash
        flask shell
        ```
        Then in the Python shell:
        ```python
        from app import db
        from app.models.user import User, UserRole
        # Ensure no user with this email exists or handle appropriately
        admin_email = 'your_admin_email@example.com' # Use the ADMIN_EMAIL from env vars or another
        admin_password = 'a_very_strong_password'
        if not User.query.filter_by(email=admin_email).first():
            u = User(email=admin_email, role=UserRole.ADMIN, email_verified=True)
            u.set_password(admin_password)
            db.session.add(u)
            db.session.commit()
            print(f"Admin user {admin_email} created.")
        else:
            print(f"User {admin_email} already exists.")
        exit()
        ```

4.  **File Uploads (Persistent Storage):**
    *   The current `render.yaml` sets `UPLOAD_FOLDER` to `/app/instance/uploads`, which uses the container's ephemeral filesystem. This means uploaded files will be **lost** on deploys or restarts.
    *   **For persistent file storage (Highly Recommended):**
        1.  Uncomment or add the `disks` section in your `render.yaml` for the web service:
            ```yaml
            services:
              - type: web
                name: pdfquill-app
                # ... other settings ...
                envVars:
                  # ...
                  - key: UPLOAD_FOLDER
                    value: /var/data/uploads # Standard mount path for Render Disks
                disks:
                  - name: pdfquill-uploads # Name your disk
                    mountPath: /var/data/uploads
                    sizeGB: 1 # Or desired size
            ```
        2.  Ensure your `UPLOAD_FOLDER` environment variable in Render matches this `mountPath`.
        3.  The application (via `Config.py`) will create this directory if it doesn't exist, but the mount must be present.

### 2. Manual Service Creation (If not using `render.yaml` directly)

If you prefer to set up services manually through the Render dashboard:

1.  **Create a PostgreSQL Database:**
    *   New -> PostgreSQL.
    *   Choose a name, plan, region. Note the database name and user.
    *   Render will provide connection details (including a connection string).

2.  **Create a Web Service:**
    *   New -> Web Service.
    *   Connect your Git repository.
    *   **Environment:** Select "Docker".
    *   **Build Command:** (Usually not needed if Dockerfile is standard)
    *   **Start Command:** Render typically infers this from the `CMD` in your Dockerfile (e.g., `gunicorn --bind 0.0.0.0:${PORT} run:app`).
    *   **Health Check Path:** Set to `/health`.
    *   **Environment Variables:**
        *   Add `DATABASE_URL` and select "From Database" -> your PostgreSQL service -> "Connection String".
        *   Add all other environment variables as listed in the `render.yaml` section above (SECRET_KEY, Paystack keys, Mail settings, etc.).
    *   **Persistent Storage (for Uploads):** Go to the "Disks" section for your web service and add a new disk. Set the `mountPath` (e.g., `/var/data/uploads`) and ensure your `UPLOAD_FOLDER` environment variable matches this path.

## Important Environment Variables (Recap)

These need to be configured in your Render web service's environment settings:

*   `SECRET_KEY`: A long, random string for Flask session security, etc. (Render can generate this).
*   `DATABASE_URL`: Provided by Render if you create a PostgreSQL service and link it.
*   `PAYSTACK_SECRET_KEY`: Your Paystack secret API key.
*   `PAYSTACK_PUBLIC_KEY`: Your Paystack public API key.
*   `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`: For sending emails.
*   `ADMIN_EMAIL`: For application admin notifications.
*   `UPLOAD_FOLDER`: Path for file uploads. For persistence, ensure it maps to a Render Disk. Example: `/var/data/uploads`.
*   `FLASK_ENV`: Should be `production`.

## Scaling Tips (Basic)

*   **Web Service Plan:** Render's paid plans offer more resources (CPU/RAM) and prevent services from sleeping. Upgrade your web service plan as traffic grows.
*   **Database Plan:** Similarly, upgrade your PostgreSQL database plan if it becomes a bottleneck.
*   **Gunicorn Workers:** The `CMD` in the Dockerfile uses `gunicorn ... --workers 2 --threads 4 ...`. The number of workers can be tuned based on your service plan's CPU cores and memory. A common starting point is `(2 * NUM_CORES) + 1` for workers. Threads help with I/O-bound operations. Monitor resource usage to optimize.
*   **Horizontal Scaling:** For higher-tier plans, Render supports horizontal scaling (running multiple instances of your web service).
*   **Content Delivery Network (CDN):** For static assets (CSS, JS, images) and potentially user-uploaded public files, using a CDN can improve performance and reduce load on your web service. Render offers a built-in CDN for static sites, but for dynamic app assets, you might integrate with services like Cloudflare or AWS CloudFront.
*   **Background Tasks:** For long-running tasks (like complex email sending, report generation), consider using Render Background Workers with a task queue like Celery and Redis.

## Troubleshooting

*   **Logs:** Check the "Logs" tab for your web service and database service in the Render dashboard for any errors.
*   **Health Checks:** If your application fails health checks, it might be crashing on startup. Review logs for startup errors.
*   **Environment Variables:** Double-check that all required environment variables are set correctly and are accessible by the application.
*   **Database Connection:** Ensure `DATABASE_URL` is correct and the web service can connect to the database (check firewall rules if any, though Render usually handles this for linked services).
*   **File Permissions:** If using Render Disks or specific upload paths, ensure your application has write permissions to the `UPLOAD_FOLDER`.

This guide provides a starting point. Always refer to the official [Render Documentation](https://render.com/docs) for the most up-to-date information.Tool output for `create_file_with_block`:
