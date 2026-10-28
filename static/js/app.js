(() => {
  const app = document.querySelector("#app");
  const currency = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });
  const money = (amount) => currency.format(Number(amount) || 0);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
  const today = new Date();
  const localDate = (date) => {
    const offset = date.getTimezoneOffset();
    return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10);
  };
  const addDays = (date, days) => {
    const result = new Date(`${date}T12:00:00`);
    result.setDate(result.getDate() + days);
    return localDate(result);
  };
  const inventory = [
    { id: "chairs", name: "Bentwood Chair", category: "Seating", description: "A timeless, comfortable chair that looks right at every table.", quantity: 100, price: 50, deposit: 250, location: "Mumbai, Maharashtra", image: "photo-1503602642458-232111445657", keywords: "chair chairs seating ceremony" },
    { id: "tables", name: "Farmhouse Table", category: "Tables", description: "A generous wood table made for a long, lovely dinner.", quantity: 20, price: 850, deposit: 1500, location: "Mumbai, Maharashtra", image: "photo-1449247709967-d4461a6a6103", keywords: "table tables dinner wood" },
    { id: "stages", name: "Modular Stage", category: "Stage & Lighting", description: "A clean, sturdy stage for speeches, music, and the big entrance.", quantity: 2, price: 4500, deposit: 8000, location: "Mumbai, Maharashtra", image: "photo-1506157786151-b8491531f063", keywords: "stage platform event" },
    { id: "speakers", name: "Portable Sound System", category: "Sound", description: "Full, clear sound for your ceremony, dinner, and dance floor.", quantity: 10, price: 1200, deposit: 3000, location: "Mumbai, Maharashtra", image: "photo-1470229722913-7c0e2dbb3a5", keywords: "speaker speakers audio sound music" },
    { id: "microphones", name: "Wireless Microphone", category: "Sound", description: "A reliable wireless microphone for toasts and announcements.", quantity: 8, price: 350, deposit: 1000, location: "Mumbai, Maharashtra", image: "photo-1598488035139-bdbb2231ce04", keywords: "microphone mic sound speech" },
    { id: "projectors", name: "HD Projector", category: "AV", description: "A bright, crisp picture for slideshows, screenings, and big ideas.", quantity: 5, price: 1800, deposit: 3500, location: "Mumbai, Maharashtra", image: "photo-1478720568477-152d9b164e26", keywords: "projector screen video av" },
    { id: "led-lights", name: "Warm LED Uplight", category: "Stage & Lighting", description: "Soft, adjustable light to bring the room into its evening mood.", quantity: 30, price: 180, deposit: 400, location: "Mumbai, Maharashtra", image: "photo-1519608487953-e999c86e7455", keywords: "led light lights lighting" },
    { id: "tents", name: "Garden Marquee Tent", category: "Outdoor", description: "Shelter your outdoor gathering without losing the open-air feeling.", quantity: 5, price: 5500, deposit: 10000, location: "Mumbai, Maharashtra", image: "photo-1519167758481-83f550bb49b3", keywords: "tent marquee outdoor canopy" },
    { id: "decorations", name: "Ceramic Bud Vase Set", category: "Decor", description: "A collection of simple vases for blooms, branches, or candlelight.", quantity: 20, price: 200, deposit: 500, location: "Mumbai, Maharashtra", image: "photo-1490750967868-88aa4486c946", keywords: "decor vase flowers decoration" },
    { id: "led-screens", name: "LED Display Screen", category: "AV", description: "A high-impact screen for your event visuals and live moments.", quantity: 3, price: 9000, deposit: 16000, location: "Mumbai, Maharashtra", image: "photo-1505373877841-8d25f7d46678", keywords: "led display screen av" },
    { id: "dining", name: "Stoneware Dinner Set", category: "Dining", description: "An understated place setting for a table that feels considered.", quantity: 60, price: 120, deposit: 250, location: "Mumbai, Maharashtra", image: "photo-1498837167922-ddd27525d352", keywords: "dining plates dinner tableware" },
    { id: "flowers", name: "Seasonal Floral Arrangement", category: "Florals", description: "A fresh centerpiece arranged with the best of the season.", quantity: 15, price: 750, deposit: 1500, location: "Mumbai, Maharashtra", image: "photo-1523438885200-e635ba2c371e", keywords: "flowers florals floral centerpiece" },
  ];
  const faqs = [
    ["How do I create an account?", "This static demo does not use real accounts. You can browse inventory and save reservation requests in this browser using My plans.", "account register signup customer"],
    ["How do I log in?", "Login is not available in this static demo. Reservations are saved only in this browser and are not linked to an online account.", "login signin password"],
    ["What items can I rent?", "Browse the inventory page for chairs, tables, staging, sound equipment, lighting, tents, decor, and dining pieces. Items and quantities shown are sample demo data.", "items rent rental inventory equipment collection"],
    ["How do I find rental items?", "Open Explore rentals to browse the collection. Select an item to see its description, daily price, security deposit, location, and date availability.", "find browse explore view items inventory"],
    ["How do I search or filter items?", "On the inventory page, use the search field to find an item by name or description. Filter by category or maximum daily price, then choose a sorting option.", "search filter category price sort inventory"],
    ["Where can I see item prices?", "Each inventory card shows the rental price per unit per day. Open an item's details to see its security deposit too. The reservation form estimates the total for your quantity and dates.", "price prices cost rate rental deposit estimate"],
    ["How do I check item availability?", "Open an item's details, enter your event date and return date, and choose Check these dates. Availability is estimated from demo reservations stored in this browser.", "availability available stock dates quantity check"],
    ["How do I make a reservation?", "Open an item, choose Request a reservation, then enter quantity and dates. Your demo request is saved in this browser only; it is not sent to Gathers & Co. or confirmed.", "reservation reserve booking book request dates"],
    ["How is rental price calculated?", "Rental cost is the item's daily price multiplied by the number of units and rental days. The per-unit security deposit is added to that rental cost. The form shows an estimate before submission.", "price cost calculate rental total days quantity"],
    ["Can I reserve multiple items?", "Yes. Submit a separate demo reservation for each item so availability and pricing are calculated separately.", "multiple items reserve reservation"],
    ["Where can I see my reservations?", "Choose My plans in the navigation. Demo reservations are stored in this browser's local storage; clearing browser data removes them.", "reservations bookings dashboard history status"],
    ["What do reservation statuses mean?", "Pending means the demo request has not been reviewed. Approved, Rejected, Cancelled, and Completed are sample statuses; there is no owner account connected to this static site.", "status pending approved rejected cancelled completed"],
    ["Can I cancel a reservation?", "You can remove a demo request from My plans in this browser. Because there is no server, the request has not been sent to an owner.", "cancel cancellation reservation booking"],
    ["How can I modify my reservation?", "Remove the demo request from My plans and submit a new one with the corrected dates or quantity.", "modify change edit update reservation"],
    ["What should I do if an item is unavailable?", "Try another date or reduce the quantity, then check availability again. Availability is only a local demo estimate.", "unavailable availability stock quantity dates"],
    ["How do I contact support?", "Use the Support page to draft a message. The static demo cannot deliver it to a support team; connect a backend or email service to enable delivery.", "support contact help ticket question"],
    ["How can an owner list inventory?", "Owner login and inventory editing are not available in this static demo. Inventory is sample data in the JavaScript file.", "owner admin add create list inventory"],
    ["How do I update an inventory listing?", "Inventory editing requires a backend and owner authentication, which are not part of this static website.", "owner admin edit update listing inventory"],
    ["Can I pay online?", "No. This demo does not process payments. All displayed totals are estimates, and no card is charged.", "payment payments pay charges checkout online"],
    ["Are demo payments real?", "No. This website does not process online payments. Reservation totals are estimates and no card is charged.", "demo payment real charge"],
    ["What is the security deposit?", "The security deposit is shown per unit on the item's detail page and added to your estimate for each unit. This is demo information only.", "deposit security refundable amount"],
    ["How long does approval take?", "There is no live approval workflow in the static demo. Requests are saved in your browser and are not reviewed by an owner.", "approval pending review time"],
    ["Can I use the assistant to get help?", "Yes. Choose Ask Gathers in the corner and enter a question. The assistant looks for answers in the built-in website FAQs. It runs locally in your browser and is not an online AI service.", "assistant chat chatbot ai ask help"],
  ];
  const terms = (text) => {
    const aliases = {
      book: "reservation", booked: "reservation", booking: "reservation", bookings: "reservation",
      canceling: "cancel", cancelled: "cancel", canceled: "cancel", cost: "price", costs: "price",
      find: "browse", listing: "inventory", listings: "inventory", pay: "payment",
      payments: "payment", rental: "rent", rentals: "rent", reserve: "reservation",
      reserved: "reservation", reserving: "reservation", stock: "availability",
      unavailable: "availability", view: "browse",
    };
    return new Set(String(text).toLowerCase().match(/[a-z0-9]+/g)?.map((word) => aliases[word] || (word.length > 3 && word.endsWith("s") ? word.slice(0, -1) : word)) || []);
  };
  const reservations = () => {
    try { return JSON.parse(localStorage.getItem("gathers-demo-reservations") || "[]"); }
    catch { return []; }
  };
  const saveReservations = (items) => localStorage.setItem("gathers-demo-reservations", JSON.stringify(items));
  const image = (item) => `https://images.unsplash.com/${item.image}?auto=format&fit=crop&w=1000&q=80`;
  const card = (item) => `<article class="item-card"><a class="item-image" href="#item/${item.id}"><img loading="lazy" src="${image(item)}" alt="${escapeHtml(item.name)}"><span class="image-tag">${escapeHtml(item.category)}</span></a><div class="item-card-body"><div><h3><a href="#item/${item.id}">${escapeHtml(item.name)}</a></h3><p>${money(item.price)} <span>/ unit / day</span></p></div><a class="round-arrow" aria-label="View ${escapeHtml(item.name)}" href="#item/${item.id}">↗</a></div><p class="item-description">${escapeHtml(item.description)}</p></article>`;
  const pageHero = (eyebrow, title, copy) => `<section class="page-hero"><span class="eyebrow">${eyebrow}</span><h1>${title}</h1><p>${copy}</p></section>`;
  const renderHome = () => `
    <section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="eyebrow-line"></span> THE GOOD STUFF, RIGHT ON TIME</div><h1>Make room for<br>a <em>good time.</em></h1><p class="hero-lead">From the first toast to the last dance, find all the little things that make your gathering feel like yours.</p><div class="hero-actions"><a class="button" href="#inventory">Explore the collection <span>↗</span></a><a class="quiet-link" href="#how-it-works">How it works <span>↓</span></a></div><div class="hero-proof"><div class="avatar-stack"><span>J</span><span>A</span><span>M</span></div><p><strong>Made for moments.</strong><br>Thoughtful pieces for good gatherings.</p></div></div><div class="hero-art"><img class="hero-image" src="https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&w=1200&q=85" alt="Beautifully set table at a garden event"><div class="floating-note"><span class="note-icon">✳</span><span><strong>Your day, your way</strong><small>Good things are in season.</small></span></div><div class="hero-stamp">Gather<br>beautifully</div></div></section>
    <section class="trust-strip"><span>THE DETAILS MAKE THE DAY</span><div><b>01</b> Thoughtful pieces</div><div><b>02</b> Simple planning</div><div><b>03</b> Here when you need us</div></section>
    <section class="section intro-section" id="how-it-works"><div class="section-heading"><div><span class="eyebrow">A LITTLE LESS TO DO</span><h2>More celebrating.<br><em>Less figuring it out.</em></h2></div><p>Everything you need to bring your gathering to life, gathered in one lovely place.</p></div><div class="steps-grid"><article class="step-card"><span class="step-num">01 / BROWSE</span><div class="step-icon">⌕</div><h3>Find your things</h3><p>Explore thoughtfully selected pieces for celebrations big, small, and somewhere in between.</p></article><article class="step-card"><span class="step-num">02 / PLAN</span><div class="step-icon">↗</div><h3>Make it yours</h3><p>Choose your dates and quantities. See a clear price estimate before you make a plan.</p></article><article class="step-card"><span class="step-num">03 / CELEBRATE</span><div class="step-icon">✳</div><h3>Enjoy the moment</h3><p>We take the logistics seriously, so you can be present for the good stuff.</p></article></div></section>
    <section class="section collection-section"><div class="section-heading"><div><span class="eyebrow">A COLLECTION WITH CHARACTER</span><h2>The little things<br>that make <em>the moment.</em></h2></div><a class="text-link" href="#inventory">Shop all rentals ↗</a></div><div class="category-grid">${["Seating", "Tables", "Stage & Lighting", "Sound", "AV", "Outdoor", "Decor", "Dining"].map((name, index) => `<a class="category-tile" href="#inventory?category=${encodeURIComponent(name)}"><span>${String(index + 1).padStart(2, "0")}</span><strong>${name}</strong><small>Find the right finishing touch.</small><i>↗</i></a>`).join("")}</div><div class="item-grid home-items">${inventory.slice(0, 6).map(card).join("")}</div></section>
    <section class="editorial"><div class="editorial-image"><img loading="lazy" src="https://images.unsplash.com/photo-1464366400600-7168b8af9bc3?auto=format&fit=crop&w=1000&q=80" alt="An intimate celebration with warm lights"></div><div class="editorial-copy"><span class="eyebrow">GOOD GATHERINGS, MADE EASIER</span><h2>We believe the best events feel <em>like you.</em></h2><p>No cookie-cutter moments. Just a little help finding the pieces that make people feel welcome, comfortable, and glad they came.</p><a class="button button-light" href="#about">A little about us <span>↗</span></a></div></section>
    <section class="section benefit-section"><div class="section-heading centered"><span class="eyebrow">FOR THE PEOPLE WHO MAKE IT HAPPEN</span><h2>Good plans deserve<br><em>good support.</em></h2></div><div class="benefit-grid"><article><span>For hosts</span><h3>More joy in the details.</h3><p>Clear price estimates, quick availability checks, and less time chasing down the things you need.</p><a class="text-link" href="#inventory">Start planning ↗</a></article><article><span>For event pros</span><h3>A partner in your corner.</h3><p>Organized inventory and a team that understands the thoughtful work behind every gathering.</p><a class="text-link" href="#support">Talk to our team ↗</a></article></div></section>
    <section class="weather-band"><div><span class="eyebrow">PLANNING SOMETHING OUTSIDE?</span><h2>Check the sky before<br>you set the table.</h2></div><form class="weather-form" id="weather-form"><label for="weather-city">Event location</label><div><input id="weather-city" placeholder="Try Mumbai" required><button class="button" type="submit">Check forecast ↗</button></div><p id="weather-result" aria-live="polite"></p></form></section><section class="cta-band"><span class="eyebrow">YOUR NEXT GOOD GATHERING STARTS HERE</span><h2>Let's make it <em>happen.</em></h2><a class="button button-light" href="#inventory">Explore inventory <span>↗</span></a></section>`;
  const renderInventory = () => {
    const params = new URLSearchParams(location.hash.split("?")[1] || "");
    const query = params.get("q") || "";
    const category = params.get("category") || "";
    const maxPrice = params.get("max") || "";
    const sort = params.get("sort") || "";
    let matches = inventory.filter((item) => {
      const searchText = `${item.name} ${item.category} ${item.description} ${item.keywords}`.toLowerCase();
      return (!query || searchText.includes(query.toLowerCase())) &&
        (!category || item.category === category) &&
        (!maxPrice || item.price <= Number(maxPrice));
    });
    if (sort === "price") matches = [...matches].sort((a, b) => a.price - b.price);
    if (sort === "name") matches = [...matches].sort((a, b) => a.name.localeCompare(b.name));
    return `${pageHero("THOUGHTFUL THINGS FOR GOOD GATHERINGS", "Find your <em>finishing touches.</em>", "Explore our collection, check your dates, and make the moment yours.")}<section class="section inventory-section"><form class="filter-bar" id="inventory-filter"><div class="filter-search"><label for="search-items">Search the collection</label><input id="search-items" name="q" value="${escapeHtml(query)}" placeholder="Try chairs, lights, tables..."></div><div><label for="category-filter">Category</label><select id="category-filter" name="category"><option value="">All categories</option>${[...new Set(inventory.map((item) => item.category))].map((name) => `<option ${category === name ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}</select></div><div><label for="price-filter">Max. price / day</label><input id="price-filter" name="max" type="number" min="0" value="${escapeHtml(maxPrice)}" placeholder="Any price"></div><div><label for="sort-filter">Sort by</label><select id="sort-filter" name="sort"><option value="">Featured</option><option value="price" ${sort === "price" ? "selected" : ""}>Price: low to high</option><option value="name" ${sort === "name" ? "selected" : ""}>Name</option></select></div><button class="button" type="submit">Find items</button></form><div class="collection-meta"><span>${matches.length} item${matches.length === 1 ? "" : "s"} to make it yours</span><span><i class="availability-dot"></i> Check exact availability on your dates</span></div><div class="item-grid">${matches.map(card).join("") || `<div class="empty-state"><span>✳</span><h2>No matches just yet.</h2><p>Try a different search or explore all categories.</p><a class="text-link" href="#inventory">Clear filters ↗</a></div>`}</div></section>`;
  };
  const renderItem = (id) => {
    const item = inventory.find((entry) => entry.id === id);
    if (!item) return renderError(404);
    const params = new URLSearchParams(location.hash.split("?")[1] || "");
    const start = params.get("start") || "";
    const end = params.get("end") || "";
    const available = start && end && end > start ? getAvailable(item, start, end) : item.quantity;
    return `<section class="section detail-layout"><div class="detail-visual"><img src="${image(item)}" alt="${escapeHtml(item.name)}"><span class="image-tag">${escapeHtml(item.category)}</span></div><div class="detail-copy"><a class="back-link" href="#inventory">← Back to collection</a><span class="eyebrow">${escapeHtml(item.category.toUpperCase())} / A GATHERS & CO. FAVORITE</span><h1>${escapeHtml(item.name)}</h1><p class="detail-price">${money(item.price)} <span>/ unit / day</span></p><p>${escapeHtml(item.description)}</p><div class="detail-facts"><div><small>Security deposit</small><strong>${money(item.deposit)} / unit</strong></div><div><small>Pickup location</small><strong>${escapeHtml(item.location)}</strong></div><div><small>In the collection</small><strong>${item.quantity} units · demo</strong></div></div><form class="availability-check" id="availability-form" data-item="${item.id}"><h3>Check availability</h3><div class="date-row"><div><label for="check-start">Event date</label><input id="check-start" name="start" type="date" min="${localDate(today)}" value="${escapeHtml(start)}" required></div><div><label for="check-end">Return date</label><input id="check-end" name="end" type="date" min="${localDate(today)}" value="${escapeHtml(end)}" required></div></div><button class="button button-outline" type="submit">Check these dates</button><p class="availability-message"><i class="availability-dot ${available === 0 ? "dot-red" : available < 5 ? "dot-yellow" : ""}"></i> ${available} demo unit${available === 1 ? "" : "s"} available${start && end ? " for your dates" : ""}</p></form><button class="button reserve-button" type="button" data-reserve="${item.id}" ${available === 0 ? "disabled" : ""}>Request a demo reservation ↗</button><p class="demo-note">Demo only: reservations are stored in this browser and are not submitted to the company.</p></div></section>`;
  };
  const renderFAQ = () => `${pageHero("THE QUICK ANSWERS", "A few things<br>you might <em>wonder.</em>", "Browse common questions about Gathers & Co. and how this website works.")}<section class="section faq-layout"><div><span class="eyebrow">GOOD TO KNOW</span><h2>Questions, meet answers.</h2><p>Need a hand with something else? Ask our local FAQ assistant or write a support note.</p><a class="text-link" href="#support">Get in touch ↗</a></div><div class="faq-list">${faqs.map(([question, answer]) => `<details><summary>${escapeHtml(question)}<span>+</span></summary><p>${escapeHtml(answer)}</p></details>`).join("")}</div></section>`;
  const renderAbout = () => `${pageHero("A NOTE FROM US", "Gathering is a<br><em>pretty good thing.</em>", "We help make the practical parts of getting together feel a little more thoughtful.")}<section class="section about-layout"><img src="https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=1100&q=80" alt="Friends celebrating together"><div><span class="eyebrow">WHY GATHERS & CO.</span><h2>It's never just a chair.</h2><p>It's where your oldest friend saves you a seat. It's a table that brings everyone together. We believe the things you rent should make a gathering feel warm, effortless, and entirely yours.</p><p>Our collection is built around the moments people remember—and our team is here to make the details feel easy.</p><a class="button" href="#inventory">Find your finishing touches ↗</a></div></section>`;
  const renderSupport = () => `${pageHero("A REAL PERSON IS JUST A NOTE AWAY", "We're here to<br><em>make it easy.</em>", "Have a question? Leave a note in this demo support form. It will stay in this browser and will not be sent.")}<section class="section support-layout"><div><span class="eyebrow">HOW CAN WE HELP?</span><h2>Tell us what's on your mind.</h2><p>This static website does not send email or create online tickets. Add a backend or form service to receive support requests.</p><div class="support-prompt"><span>✳</span><div><strong>Need a quick answer?</strong><p>Ask the Gathers &amp; Co. FAQ assistant in the corner.</p></div></div></div><div class="form-card"><form id="support-form" class="stack-form"><p><label for="support-name">Your name</label><input id="support-name" name="name" required maxlength="100"></p><p><label for="support-email">Email</label><input id="support-email" name="email" type="email" required maxlength="180"></p><p><label for="support-message">How can we help?</label><textarea id="support-message" name="message" rows="5" required maxlength="1500"></textarea></p><button class="button">Save demo note</button></form></div></section>`;
  const renderContact = () => `${pageHero("LET'S TALK", "Good things start<br>with a <em>hello.</em>", "Have an event in mind, need a hand, or just want to say hi?") }<section class="section centered"><p>Contact details can be configured here when your business email and phone are ready.</p><a class="button" href="#support">Write us a note ↗</a></section>`;
  const renderReservations = () => {
    const saved = reservations();
    return `<section class="section reservations-page"><span class="eyebrow">YOUR PLANS, SAVED IN THIS BROWSER</span><div class="section-heading"><h1>Your reservations.</h1><a class="button button-small" href="#inventory">Find something lovely ↗</a></div><p class="demo-note">Demo only. These requests are not sent to an owner or confirmed. Your browser stores the following list locally.</p>${saved.length ? saved.map((reservation) => {
      const item = inventory.find((entry) => entry.id === reservation.itemId);
      return `<article class="reservation-row"><div class="reservation-row-main"><span class="reservation-id">DEMO · ${new Date(reservation.createdAt).toLocaleDateString("en-IN")}</span><h2>${escapeHtml(item?.name || "Event item")}</h2><p>${reservation.quantity} unit${reservation.quantity === 1 ? "" : "s"} · ${escapeHtml(reservation.eventDate)} — ${escapeHtml(reservation.returnDate)}</p></div><div class="reservation-row-side"><span class="status-pill status-pending">Demo request</span><strong>${money(reservation.total)}</strong><button class="text-button" type="button" data-remove="${reservation.id}">Remove</button></div></article>`;
    }).join("") : `<div class="empty-state"><span>✳</span><h2>Nothing on the calendar yet.</h2><p>Explore the collection and save a demo reservation here.</p><a class="button" href="#inventory">Browse the collection</a></div>`}</section>`;
  };
  const renderDashboard = () => {
    const saved = reservations();
    const total = saved.reduce((sum, entry) => sum + Number(entry.total), 0);
    return `<section class="section narrow-section"><span class="eyebrow">BROWSER-ONLY DEMO</span><h1>Your dashboard.</h1><p>This static version has no account system. Your plan data is saved locally in this browser.</p><div class="stat-grid"><article><span>Demo reservations</span><strong>${saved.length}</strong><small>Saved in this browser</small></article><article><span>Estimated total</span><strong>${money(total)}</strong><small>Not a payment</small></article><article><span>Account</span><strong>Guest</strong><small>No sign-in required</small></article></div><div class="table-heading"><h2>Continue planning</h2><a href="#reservations">My reservations ↗</a></div><a class="button" href="#inventory">Explore rentals</a></section>`;
  };
  const renderHealth = () => `${pageHero("ABOUT THIS DEMO", "A simple static<br><em>website.</em>", "Gathers & Co. is running as plain HTML, CSS, and JavaScript. No Django server or database is used.")}<section class="section"><div class="health-list"><div><span>Website</span><strong class="status-ok">Available</strong></div><div><span>Reservation storage</span><strong>Browser only</strong></div><div><span>FAQ assistant</span><strong>Built-in FAQ matching</strong></div><div><span>Online payment</span><strong>Not enabled</strong></div><div><span>Support delivery</span><strong>Not enabled</strong></div></div></section>`;
  const renderError = (code) => `<section class="error-page"><div class="error-art"><span>✳</span><i></i><b></b></div><span class="eyebrow">LET'S GET YOU BACK ON TRACK</span><strong class="error-code">${code}</strong><h1>${code === 404 ? "That page couldn't be found." : "Something went wrong."}</h1><p>Return home or ask the assistant a question.</p><div class="hero-actions"><a class="button" href="#home">Go home</a><a class="button button-outline" href="#inventory">Browse inventory</a><button type="button" class="quiet-link" data-open-chat>Ask the assistant ↗</button></div></section>`;
  const render = () => {
    const [route, query] = location.hash.slice(1).split("?");
    const page = route || "home";
    if (page === "home") app.innerHTML = renderHome();
    else if (page === "inventory") app.innerHTML = renderInventory();
    else if (page.startsWith("item/")) app.innerHTML = renderItem(page.slice(5));
    else if (page === "faq" || page === "faqs") app.innerHTML = renderFAQ();
    else if (page === "about") app.innerHTML = renderAbout();
    else if (page === "support") app.innerHTML = renderSupport();
    else if (page === "contact") app.innerHTML = renderContact();
    else if (page === "reservations") app.innerHTML = renderReservations();
    else if (page === "dashboard") app.innerHTML = renderDashboard();
    else if (page === "health") app.innerHTML = renderHealth();
    else app.innerHTML = renderError(404);
    document.title = `${page.startsWith("item/") ? inventory.find((item) => item.id === page.slice(5))?.name || "Item" : ({ home: "Make room for a good time", inventory: "The collection", faq: "FAQs", faqs: "FAQs", about: "Our story", support: "Support", contact: "Contact", reservations: "My plans", dashboard: "Dashboard", health: "Site information" }[page] || "Page not found")} — Gathers & Co.`;
    if (page === "inventory" && query) document.getElementById("inventory-filter")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    app.focus({ preventScroll: true });
  };
  const getAvailable = (item, start, end) => {
    const used = reservations()
      .filter((entry) => entry.itemId === item.id && entry.eventDate < end && entry.returnDate > start)
      .reduce((sum, entry) => sum + Number(entry.quantity), 0);
    return Math.max(0, item.quantity - used);
  };
  const toast = (message) => {
    const region = document.querySelector("#toast-region");
    const item = document.createElement("div");
    item.className = "message";
    item.textContent = message;
    region.replaceChildren(item);
    window.setTimeout(() => item.remove(), 3500);
  };
  const assistantAnswer = (question) => {
    const asked = terms(question);
    const ranked = faqs.map((faq) => {
      const questionTerms = terms(faq[0]);
      const keywordTerms = terms(faq[2]);
      const score = [...asked].reduce((sum, term) =>
        sum + (questionTerms.has(term) ? 3 : 0) + (keywordTerms.has(term) ? 2 : 0), 0);
      return { faq, score };
    }).filter((entry) => entry.score >= 3).sort((a, b) => b.score - a.score);
    return ranked.length
      ? ranked[0].faq[1]
      : "I couldn't find that in the website FAQs. This static demo cannot create a real support ticket. Use the Support page to draft a note, or contact the company directly.";
  };
  const chatPanel = document.querySelector("#chat-panel");
  const chatLauncher = document.querySelector("#chat-launcher");
  const openChat = () => {
    chatPanel.hidden = false;
    chatLauncher.setAttribute("aria-expanded", "true");
    document.querySelector("#chat-input").focus();
  };
  const closeChat = () => {
    chatPanel.hidden = true;
    chatLauncher.setAttribute("aria-expanded", "false");
    chatLauncher.focus();
  };
  chatLauncher.addEventListener("click", () => chatPanel.hidden ? openChat() : closeChat());
  document.querySelector("#chat-close").addEventListener("click", closeChat);
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-chat]")) openChat();
  });
  const addBubble = (message, kind) => {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${kind}-bubble`;
    bubble.textContent = message;
    const messages = document.querySelector("#chat-messages");
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  };
  let latestAnswer = null;
  document.querySelector("#chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.querySelector("#chat-input");
    const question = input.value.trim();
    if (!question) return;
    addBubble(question, "user");
    input.value = "";
    const answer = assistantAnswer(question);
    addBubble(answer, "assistant");
    latestAnswer = { question, answer };
    const feedback = document.querySelector("#chat-feedback");
    feedback.hidden = false;
  });
  document.querySelector("#chat-feedback").addEventListener("click", (event) => {
    const button = event.target.closest("[data-rating]");
    if (!button || !latestAnswer) return;
    try {
      const ratings = JSON.parse(localStorage.getItem("gathers-demo-feedback") || "[]");
      ratings.push({ ...latestAnswer, rating: button.dataset.rating, createdAt: new Date().toISOString() });
      localStorage.setItem("gathers-demo-feedback", JSON.stringify(ratings.slice(-100)));
      document.querySelector("#chat-feedback").innerHTML = "<span>Thanks for your feedback. Saved in this browser.</span>";
    } catch {
      document.querySelector("#chat-status").textContent = "Browser storage is unavailable.";
    }
  });

  document.addEventListener("click", (event) => {
    const reserveButton = event.target.closest("[data-reserve]");
    if (reserveButton) {
      const item = inventory.find((entry) => entry.id === reserveButton.dataset.reserve);
      if (!item) return;
      const start = document.querySelector("#check-start")?.value || "";
      const end = document.querySelector("#check-end")?.value || "";
      if (!start || !end || end <= start) {
        toast("Choose an event date and a later return date first.");
        document.querySelector("#check-start")?.focus();
        return;
      }
      const available = getAvailable(item, start, end);
      if (available < 1) {
        toast("No demo inventory is available for those dates.");
        return;
      }
      openReservationForm(item, start, end, available);
      return;
    }
    const removeButton = event.target.closest("[data-remove]");
    if (removeButton) {
      saveReservations(reservations().filter((entry) => entry.id !== removeButton.dataset.remove));
      render();
      toast("Demo request removed from this browser.");
    }
  });
  const openReservationForm = (item, start, end, available) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-backdrop";
    overlay.innerHTML = `<section class="form-card reserve-modal" role="dialog" aria-modal="true" aria-labelledby="reserve-title"><button type="button" class="modal-close" aria-label="Close">×</button><span class="eyebrow">BROWSER-ONLY DEMO</span><h2 id="reserve-title">Request ${escapeHtml(item.name)}</h2><p>This request will not be sent or confirmed.</p><form id="reserve-form" class="stack-form" data-price="${item.price}" data-deposit="${item.deposit}" data-item="${item.id}"><p><label for="reserve-quantity">Quantity (up to ${available} available)</label><input id="reserve-quantity" type="number" name="quantity" min="1" max="${available}" value="1" required></p><p><label for="reserve-start">Event date</label><input id="reserve-start" type="date" name="eventDate" min="${localDate(today)}" value="${escapeHtml(start)}" required></p><p><label for="reserve-end">Return date</label><input id="reserve-end" type="date" name="returnDate" min="${addDays(start, 1)}" value="${escapeHtml(end)}" required></p><p><label for="reserve-note">Notes (optional)</label><textarea id="reserve-note" name="notes" rows="3" maxlength="500"></textarea></p><div class="estimate-box"><div><span>Rental estimate</span><strong id="rental-estimate">${money(0)}</strong></div><div><span>Security deposit</span><strong id="deposit-estimate">${money(0)}</strong></div><div class="estimate-total"><span>Estimated total</span><strong id="total-estimate">${money(0)}</strong></div></div><button class="button" type="submit">Save demo request ↗</button></form></section>`;
    document.body.appendChild(overlay);
    const form = overlay.querySelector("#reserve-form");
    const updateEstimate = () => {
      const quantity = Math.min(Number(form.elements.quantity.value) || 0, available);
      const eventDate = form.elements.eventDate.value;
      const returnDate = form.elements.returnDate.value;
      const days = eventDate && returnDate && returnDate > eventDate
        ? (new Date(`${returnDate}T12:00:00`) - new Date(`${eventDate}T12:00:00`)) / 86400000
        : 0;
      const rental = quantity * item.price * days;
      const deposit = quantity * item.deposit;
      overlay.querySelector("#rental-estimate").textContent = money(rental);
      overlay.querySelector("#deposit-estimate").textContent = money(deposit);
      overlay.querySelector("#total-estimate").textContent = money(rental + deposit);
    };
    form.addEventListener("input", updateEstimate);
    updateEstimate();
    overlay.querySelector(".modal-close").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const quantity = Number(form.elements.quantity.value);
      const eventDate = form.elements.eventDate.value;
      const returnDate = form.elements.returnDate.value;
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > available || returnDate <= eventDate) {
        toast("Check the quantity and dates, then try again.");
        return;
      }
      const total = quantity * item.price * ((new Date(`${returnDate}T12:00:00`) - new Date(`${eventDate}T12:00:00`)) / 86400000) + quantity * item.deposit;
      const saved = reservations();
      saved.push({
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        itemId: item.id,
        quantity,
        eventDate,
        returnDate,
        total,
        notes: form.elements.notes.value,
        createdAt: new Date().toISOString(),
      });
      try {
        saveReservations(saved);
        overlay.remove();
        location.hash = "#reservations";
        toast("Demo request saved in this browser only.");
      } catch {
        toast("Could not save this request. Check browser storage settings.");
      }
    });
    overlay.querySelector("#reserve-quantity").focus();
  };

  document.addEventListener("submit", (event) => {
    if (event.target.id === "inventory-filter") {
      event.preventDefault();
      const data = new FormData(event.target);
      const params = new URLSearchParams([...data.entries()].filter(([, value]) => value));
      location.hash = `#inventory${params.size ? `?${params}` : ""}`;
    }
    if (event.target.id === "availability-form") {
      event.preventDefault();
      const data = new FormData(event.target);
      const start = String(data.get("start"));
      const end = String(data.get("end"));
      if (end <= start) {
        toast("Return date must be after the event date.");
        return;
      }
      location.hash = `#item/${event.target.dataset.item}?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
    }
    if (event.target.id === "support-form") {
      event.preventDefault();
      const data = new FormData(event.target);
      const note = Object.fromEntries(data.entries());
      try {
        const messages = JSON.parse(localStorage.getItem("gathers-demo-support") || "[]");
        messages.push({ ...note, createdAt: new Date().toISOString() });
        localStorage.setItem("gathers-demo-support", JSON.stringify(messages.slice(-20)));
        event.target.reset();
        toast("Demo note saved in this browser. It was not sent.");
      } catch {
        toast("Could not save the demo note in this browser.");
      }
    }
    if (event.target.id === "weather-form") {
      event.preventDefault();
      getWeather(event.target);
    }
  });
  const getWeather = async (form) => {
    const output = document.querySelector("#weather-result");
    output.textContent = "Checking the forecast…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const city = form.querySelector("#weather-city").value.trim();
      const geoResponse = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`, { signal: controller.signal });
      if (!geoResponse.ok) throw new Error("Weather lookup failed");
      const place = (await geoResponse.json()).results?.[0];
      if (!place) throw new Error("No matching location");
      const weatherResponse = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}&daily=temperature_2m_max,precipitation_probability_max,weather_code&timezone=auto&forecast_days=1`, { signal: controller.signal });
      if (!weatherResponse.ok) throw new Error("Forecast unavailable");
      const forecast = (await weatherResponse.json()).daily;
      const conditions = { 0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 51: "Light drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain", 80: "Rain showers", 95: "Thunderstorm" };
      output.textContent = `${place.name}: ${forecast.temperature_2m_max[0]}°C · ${conditions[forecast.weather_code[0]] || "Weather update"} · ${forecast.precipitation_probability_max[0]}% chance of rain.`;
    } catch {
      output.textContent = "Weather information is temporarily unavailable.";
    } finally {
      clearTimeout(timeout);
    }
  };

  const menuToggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".main-nav");
  menuToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("nav-open");
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      nav.classList.remove("nav-open");
      menuToggle.setAttribute("aria-expanded", "false");
    }
  });
  window.addEventListener("hashchange", render);
  document.querySelector("#current-year").textContent = new Date().getFullYear();
  render();
})();
