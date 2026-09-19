# Post content format (Gutenberg blocks)

WordPress stores post bodies as Gutenberg block markup — HTML wrapped in `<!-- wp:* -->` comment delimiters. Use this format for the content file passed to `scripts/create-post.sh` or a round-trip edit.

```html
<!-- wp:paragraph -->
<p>Paragraph text here.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Section Heading</h2>
<!-- /wp:heading -->

<!-- wp:code -->
<pre class="wp-block-code"><code>code here</code></pre>
<!-- /wp:code -->

<!-- wp:list -->
<ul>
<li>List item</li>
</ul>
<!-- /wp:list -->
```

## Author signature (Automated via Theme Template)

**Architectural Update (Option 1 Migration):**
AI attribution signatures are now rendered **automatically at the theme template layer** (`content-single.blade.php`) based on the assigned post author:
- `gemini-ai` -> Renders: `Written by Gemini 3.8 Flash — AI systems engineer pair-programming with Eddy Kawira on workstation`
- `groot` -> Renders: `Written by Groot — OpenClaw agent pair-programming with Eddy Kawira`
- `claude-ai` -> Renders: `Written by Claude Sonnet 4.5 — AI assistant pair-programming with Eddy Kawira`

**Do NOT manually hardcode signature blocks in the post content body.** Simply assign the post author when creating or updating the post:
```bash
wp post create ... --post_author=4  # 4 = gemini-ai, 3 = groot, 2 = claude-ai, 1 = eddygk
```

## Block Delimiter Integrity & Pre-Flight Validation

**CRITICAL**: Every Gutenberg block opening delimiter (`<!-- wp:paragraph -->`, `<!-- wp:heading -->`, `<!-- wp:separator -->`, etc.) **MUST** have its corresponding closing delimiter (`<!-- /wp:paragraph -->`, `<!-- /wp:heading -->`, `<!-- /wp:separator -->`), except self-closing blocks (`<!-- wp:separator /-->`).

If a block delimiter is left unclosed:
- Gutenberg treats subsequent content as nested `innerBlocks`.
- When WordPress 6.5+ runs `apply_block_hooks_to_content_from_post_object`, trailing content (like the signature) will cascade and re-render multiple times.

Always validate files before publishing using:
```bash
python3 scripts/validate-gutenberg.py <file.html>
```
`scripts/create-post.sh` automatically enforces this check prior to creating or updating posts.

---

## RFC-Compliant Placeholders & Sanitization SOP

When publishing technical architectures, command-line snippets, configuration files, or logs, **NEVER leak real infrastructure details, internal IP subnets, hardware serials/MACs, client domains, or live tokens**. Furthermore, **never use synthetic hex strings that mimic real UUIDs**, as they trigger security scanner alerts and user credential exposure concerns.

All blog posts, guides, and documentation must adhere to the following RFC-compliant placeholder standards:

### 1. Domain Names (RFC 2606 & RFC 6761)
- **Use:** `example.com`, `example.net`, `example.org` or `.example` (e.g., `app.example.com`, `internal.example.com`, `yourdomain.com`).
- **Never use:** Real client domains, staging URLs, or unregistered private domains.

### 2. Public / External IP Addresses (RFC 5737 & RFC 3849)
- **IPv4 Documentation Blocks:**
  - `192.0.2.0/24` (TEST-NET-1)
  - `198.51.100.0/24` (TEST-NET-2)
  - `203.0.113.0/24` (TEST-NET-3) — *Primary choice for public WAN/nmap scan examples.*
- **IPv6 Documentation Prefix:** `2001:db8::/32`
- **Never use:** Real residential or datacenter WAN IP addresses.

### 3. Private / Internal IP Networks (RFC 1918)
- **Use Generic Documentation Subnets:**
  - DMZ / Containers: `10.0.10.0/24` (Gateway: `10.0.10.1`, Workloads: `10.0.10.10`, `10.0.10.50`)
  - Management Plane: `10.0.1.0/24` (or `192.168.10.0/24`)
  - Workstation / LAN: `192.168.1.0/24` (Host: `192.168.1.100`)
  - Hyper-V WinNAT: `172.16.10.0/24` (Gateway: `172.16.10.1`, Hosts: `172.16.10.10`)
- **Never use:** Real production subnets or actual router/host IP addresses.

### 4. MAC Addresses & Hardware Identifiers (RFC 7042)
- **Use:** `00:53:00:XX:XX:XX` (RFC 7042 documentation range) or generic vendor mask `00:16:3E:XX:XX:XX`.
- **Never use:** Real hardware NIC MAC addresses or physical switch port names.

### 5. Tokens, Secret Keys, and UUIDs (Explicit Bracketed Placeholders)
- **Format:** Always wrap uppercase semantic descriptors in angle brackets:
  - `<YOUR-TUNNEL-UUID>`
  - `<YOUR-TUNNEL-TOKEN>`
  - `<jwt-assertion-token>`
  - `<api-key>`
  - `<pbs-datastore>`
  - `<datastore-name>`
  - `<hypervisor-ip>`
- **Never use:** Synthetic or generated UUID hex strings (e.g., `7b8a1234-abcd-...`) that look like live production credentials.

### 6. Email Addresses (RFC 2606)
- **Use:** `user@example.com`, `admin@example.com`.
- **Never use:** Real personal or administrator email addresses.

### 7. Physical Locations & Living Spaces
- **Use:** Generic site and environment descriptors: `the primary physical site`, `the previous site`, `workstation VM`, `nested hypervisor VM`, `local lab environment`.
- **Never use:** Real street names, city/site nicknames, or personal room labels.

### 8. Personal Hardware Specs & Chassis Models
- **Use:** Generic hardware architecture descriptions:
  - `8-core desktop workstation` (instead of specific retail CPU models)
  - `dedicated GPU compute node` / `workstation GPU` (instead of consumer GPU brands)
  - `1U enterprise rack server` / `bare-metal rack server` (instead of enterprise chassis model tags)
  - `external 2 TB USB 3.0 hard drive` (instead of retail drive brands)
- **Never use:** Specific desktop/chassis hardware brands, processor models, or storage drive labels in public infrastructure essays.

### 9. Internal Hostnames, Daemon Identifiers, and Container IDs (CTIDs)
- **Use:** Standardized documentation aliases:
  - Hypervisors: `primary-hypervisor`, `primary hypervisor node` (instead of internal node tags)
  - Backup servers: `pbs-node`, `pbs-storage` (instead of internal backup hostnames)
  - Workstations: `workstation host`, `Windows workstation` (instead of private NetBIOS names)
  - Tunnels: `homelab-ingress`, `prod-tunnel-gateway` (instead of internal tunnel daemon names)
  - Containers & disks: `CT 100`, `CT 101`, `vm-101-disk-0` (instead of production IDs)
- **Never use:** Real internal hostnames, cluster node identifiers, or production container IDs.

### 10. The Full-Surface Sanitization Invariant (Audit All Layers)
Sanitization must NOT be confined to `post_content`. When drafting, editing, or auditing content, verify all 7 layers:
1. **`post_content`**: The post or page body markup.
2. **`post_title` & `post_excerpt`**: Header titles and summary excerpts.
3. **`wp_postmeta`**:
   - `_yoast_wpseo_metadesc` (SEO meta descriptions shown on search engines and social cards).
   - `_yoast_wpseo_title` & `_yoast_wpseo_focuskw`.
   - `_tldr_takeaways` (serialized PHP arrays rendered by theme key takeaway blocks).
   - Custom meta fields (e.g. `lab_tab_*`).
4. **Media Library Attachments**:
   - `_wp_attachment_image_alt` (image alt tags stored in `wp_postmeta` and rendered into HTML).
   - Image captions and attachment post titles.
5. **Theme Templates & Views (`resources/views/**/*.blade.php`)**:
   - Never hardcode private IPs (e.g. in `footer.blade.php`).
   - Never render dynamic server environment variables like `$_SERVER['SERVER_ADDR']` (e.g. in `404.blade.php`).
6. **Forms & Notifications**:
   - Form field defaults, email notification recipients, and sender headers (`_mail`, `_mail_2`).
7. **Local Draft Markdown Files**:
   - Local drafts in `business/blog-drafts/*.md` must be kept in 100% synchronization with sanitized database values to prevent re-infecting posts upon future updates.

### 11. Automated Pre-Flight Linter
All drafts and content updates must pass the automated security linter before publishing:
```bash
python3 scripts/validate-sanitization.py <file.html|file.md>
```
`scripts/create-post.sh` and `scripts/set-post-meta.sh` automatically enforce this linter. Any script detecting forbidden patterns will abort execution and output the exact line number and offending snippet.


