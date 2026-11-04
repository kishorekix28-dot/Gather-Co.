"""Initial knowledge base, loaded by data migration 0002."""

FAQS = [
    ("Products", "How do I add a new product?",
     "Go to Products and click **Add product** (administrators only). Enter the name, a unique SKU, category, "
     "supplier, selling price, purchase cost, minimum stock level, optional description and image, plus the "
     "opening stock. Click **Save product**. Duplicate SKUs are rejected automatically.",
     "add product, create product, new item, register product"),
    ("Products", "How do I update product details?",
     "Open the product from the Products list and click **Edit**. You can change the name, SKU, category, "
     "supplier, price, cost, minimum stock level, description and image. Quantities are changed through "
     "stock transactions so every movement is recorded.",
     "edit product, change price, rename product, product details"),
    ("Stock", "How do I record stock-in?",
     "Open **Transactions → Record movement** (or click **Stock in** on a product), choose the product, select "
     "type **Stock In**, enter the quantity received, optionally the supplier, unit cost and a PO/invoice "
     "reference, then save. The quantity is increased and the movement is logged in stock history.",
     "update stock, add stock, receive goods, restock, purchase, increase quantity, edit stock"),
    ("Stock", "How do I record stock-out?",
     "Open **Transactions → Record movement**, choose the product, select type **Stock Out**, enter the quantity "
     "issued or sold and an optional order reference, then save. The system blocks any stock-out that would "
     "make the quantity negative.",
     "remove stock, sell, dispatch, issue goods, reduce quantity, decrease stock"),
    ("Stock", "How do I check low-stock products?",
     "The Dashboard shows low-stock and out-of-stock counts and an alert list, and the bell icon in the top bar "
     "lists products needing attention. On the Products page use the **Stock status → Low stock** filter, or "
     "open **Reports → Low-stock products**. A product is low on stock when its quantity is at or below its "
     "minimum stock level.",
     "low stock, alerts, reorder, minimum level, running out, out of stock"),
    ("Products", "How do I delete a product?",
     "Administrators can open the product and click **Delete**, then confirm. Deleting a product also removes "
     "its stock transactions, so consider setting stock to zero instead if you need to keep the history.",
     "remove product, delete item, erase product"),
    ("Suppliers", "How do I add a supplier?",
     "Go to **Suppliers** and click **Add supplier** (administrators only). Enter the company name, contact "
     "person, email, phone, website, address and notes, then save. Suppliers can then be linked to products "
     "and stock-in transactions to build their purchase history.",
     "new supplier, add vendor, create supplier, supplier contact"),
    ("Reports", "How do I export inventory reports?",
     "Open **Reports**, pick a report (current inventory, stock-in, stock-out, low stock, valuation or product "
     "movement), optionally set a date range, then click **Export CSV**. The file opens in Excel or Google Sheets.",
     "export, csv, download report, excel, export inventory"),
    ("Account", "How do I change my password?",
     "Click your name in the top-right corner and choose **My profile**. Enter your current password and the "
     "new password twice, then click **Change password**. Passwords must be at least 8 characters and not "
     "too common.",
     "change password, reset password, update password, account security"),
    ("Stock", "How do I view inventory history?",
     "Open **Transactions** to see every stock-in, stock-out and adjustment with date, user, before/after "
     "quantities and references. Filter by type, product/SKU or date range. Each product page also shows its "
     "own movement history, and **Reports → Product movement** summarises it.",
     "history, stock history, transaction log, audit, movement history, inventory history"),
    ("Stock", "How do I adjust stock after a physical count?",
     "Administrators can choose **Record movement → Adjustment** and enter the counted quantity. The system "
     "records the difference as an adjustment so the audit trail stays complete.",
     "stock adjustment, stock count, stocktake, correct quantity, fix stock"),
    ("Categories", "How do I manage categories?",
     "Open **Categories** to search categories and see how many products each has. Administrators can add, "
     "edit or delete categories; deleting a category keeps its products but leaves them uncategorised. Click a "
     "category to view its products.",
     "add category, edit category, delete category, category products, group"),
    ("Support", "How do I contact support or raise a ticket?",
     "Open **Support Tickets → New ticket**, describe the problem and choose a priority. You can follow the "
     "status (Open, In Progress, Waiting for Response, Resolved, Closed) and read the admin response there. The "
     "assistant also creates a ticket automatically when it cannot answer a question.",
     "support ticket, contact support, help desk, raise ticket, complaint"),
]

ERROR_CODES = [
    (400, "Bad Request",
     "The server could not process the request because it was malformed or contained invalid data.",
     "Missing or invalid form fields, malformed JSON sent to the API, or an invalid query parameter.",
     "Check the highlighted form fields, correct the values and submit again. API clients should validate "
     "their JSON payloads."),
    (401, "Unauthorized",
     "The request requires you to be signed in, or your credentials were not accepted.",
     "You are not logged in, your session has expired, or the username/password is incorrect.",
     "Log in again from the Login page. If you forgot your password, ask an administrator to reset it."),
    (403, "Forbidden",
     "You are signed in but your role does not have permission to perform this action.",
     "A staff account tried to use an administrator feature (e.g. deleting products, managing users or "
     "suppliers), or the CSRF security token was missing or expired.",
     "Ask an administrator for access, or refresh the page and try again if the form was open for a long time."),
    (404, "Page Not Found",
     "The page or record you requested does not exist.",
     "A mistyped URL, an outdated bookmark, or the product/ticket was deleted.",
     "Check the address, use the navigation menu or search, or return to the Dashboard."),
    (405, "Method Not Allowed",
     "The URL exists but does not accept the HTTP method that was used.",
     "Sending a GET request to an endpoint that only accepts POST (for example logout or delete), or "
     "calling a read-only API endpoint with POST/PUT/DELETE.",
     "Use the buttons and forms in the application, or use the HTTP method documented for the API endpoint."),
    (408, "Request Timeout",
     "The server waited too long for the request to complete.",
     "A slow or unstable network connection, or a very large upload such as an oversized product image.",
     "Check your internet connection, reduce the image size (max 3 MB) and try again."),
    (429, "Too Many Requests",
     "You have sent too many requests in a short period and have been temporarily rate limited.",
     "Rapidly repeated API calls or sending many chat messages in quick succession.",
     "Wait about a minute before trying again. Automated scripts should slow down their request rate."),
    (500, "Internal Server Error",
     "Something went wrong on the server while processing your request.",
     "An unexpected application error, a database problem or a failing external service.",
     "Try again in a few minutes. If it keeps happening, raise a support ticket describing what you were doing; "
     "the error has been logged for the administrators."),
]

HELP_ARTICLES = [
    ("Why is my product not appearing?",
     "product not appearing, missing product, cannot find product, product not showing, hidden product, not visible",
     "If a product is not appearing in the Products list: (1) clear the search box and the category / stock "
     "status filters, (2) check the other pages of the list – results are paginated 10 per page, (3) search by "
     "the exact SKU, (4) check that the product was saved – a duplicate SKU or invalid price stops the save and "
     "shows an error, and (5) ask an administrator whether it was deleted (see Dashboard → Recent activity)."),
    ("Roles and permissions",
     "roles, permissions, admin, staff, access, cannot delete, not allowed",
     "There are two roles. ADMIN users can manage products, categories, suppliers, users, FAQs, error codes, "
     "reports and all support tickets. STAFF users can view inventory and products, record stock-in and "
     "stock-out, create support tickets and use the assistant. Administrators change roles under Users."),
    ("Inventory valuation and currencies",
     "valuation, inventory value, currency, exchange rate, worth, total value",
     "Inventory value is calculated as purchase cost × quantity for every product. The Dashboard shows the "
     "total and Reports → Inventory valuation breaks it down by category. The Reports page also converts the "
     "valuation into other currencies using live exchange rates, with reference rates used if the rate service "
     "is unavailable."),
    ("Using the dashboard",
     "dashboard, overview, charts, statistics, monthly, summary",
     "The Dashboard summarises total products, units in stock, inventory value, low-stock and out-of-stock "
     "counts and categories, plus charts of stock status, monthly stock-in/out and value by category, recent "
     "transactions and recent activity."),
]
