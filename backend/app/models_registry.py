"""Import model modules here before creating tables or running migrations."""

import app.core.numbering  # noqa: F401
import app.modules.billing.models  # noqa: F401
import app.modules.catalog.models  # noqa: F401
import app.modules.deliveries.models  # noqa: F401
import app.modules.installs.models  # noqa: F401
import app.modules.inventory.models  # noqa: F401
import app.modules.orders.models  # noqa: F401
import app.modules.quotes.models  # noqa: F401
import app.modules.surveys.models  # noqa: F401
import app.modules.tickets.models  # noqa: F401
import app.modules.users.models  # noqa: F401
import app.modules.portal.models  # noqa: F401
import app.modules.warranty.models  # noqa: F401

# Person D modules
import app.modules.leads.models  # noqa: F401
import app.modules.subsidy.models  # noqa: F401
# public and reports have no new tables
