from urllib.parse import urlparse

TRUSTED_DOMAINS = {
    "microsoft.com",
    "learn.microsoft.com",
    "cloud.google.com",
    "cloudskillsboost.google",
    "aws.amazon.com",
    "skillbuilder.aws",
    "coursera.org",
    "edx.org",
    "tryhackme.com",
    "hackthebox.com",
    "mlh.io",
    "devpost.com",
    "eventbrite.com",
    "meetup.com",
    "cisco.com",
    "netacad.com",
    "isc2.org",
    "comptia.org",
    "owasp.org",
    "nvidia.com",
    "huggingface.co",
    "kaggle.com",
    "github.com",
    "linkedin.com",
}


def get_source_domain(url: str) -> str:
    if not url:
        return ""
    if "://" not in url and not url.startswith("//"):
        url = "http://" + url
    parsed = urlparse(url)
    netloc = parsed.netloc or parsed.path.split("/")[0]
    domain = netloc.split(":")[0].lower().strip()
    return domain


def is_trusted(url: str) -> bool:
    domain = get_source_domain(url)
    if not domain:
        return False
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            return True
    return False
