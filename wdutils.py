import os
from enum import StrEnum
from wikidot import *
from wikidot.common.exceptions import WikidotStatusCodeException, NotFoundException
from wikidot.module.site import Site, SiteApplication
from constants import *

class ApplAction(StrEnum):
    REJECT = "decline"
    ACCEPT = "accept"

# Helper function that rejects/accepts an application using a site object
# (We need this because apparently the wikidot-py application feature was never tested or broke at some point)
def wd_appl_action(application: SiteApplication, site: Site, action: ApplAction, text: str = None):
    if text != None:
        message = text
    else:
        message = MESSAGE_REJECT_DEFAULT if action == ApplAction.REJECT else MESSAGE_ACCEPT_DEFAULT
    try:
        site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "acceptApplication",
                    "user_id": application.user.id,
                    "text": message,
                    "type": action,
                    "moduleName": "Empty",
                }
            ]
        )
    except WikidotStatusCodeException as e:
        if e.status_code == "no_application":
            raise NotFoundException(
                f"Application not found: {application.user.name}"
            ) from e
        else:
            raise e
