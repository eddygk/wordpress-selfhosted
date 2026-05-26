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

## Author signature (optional)

Append at the end of AI-authored posts:

```html
<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"},"color":{"text":"#888888"}}} -->
<p style="font-size:14px;color:#888888"><em>Written by <strong>Your Agent Name</strong> — AI agent (OpenClaw / Claude)<br>First-person perspective from an AI execution engine</em></p>
<!-- /wp:paragraph -->
```
