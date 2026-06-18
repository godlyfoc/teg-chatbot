import { useState } from "react";
import { PROXY_URL, SITE_HOSTNAME, WEBSITE_URL } from "@/config/site";

export default function SiteFrame() {
  const [loading, setLoading] = useState(true);

  return (
    <main className="site-frame">
      <div className={`loader${loading ? "" : " hidden"}`}>
        <div className="loader__spinner" />
        <p>Loading {SITE_HOSTNAME}…</p>
      </div>

      <iframe
        src={PROXY_URL}
        title={`${SITE_HOSTNAME} preview`}
        className="site-frame__iframe"
        onLoad={() => setLoading(false)}
      />

      <a
        href={WEBSITE_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="open-site-link"
      >
        Open site ↗
      </a>
    </main>
  );
}
