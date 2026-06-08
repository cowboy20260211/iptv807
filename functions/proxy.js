const UPSTREAM = 'https://iptv807.com';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const upstreamUrl = new URL(UPSTREAM);
  upstreamUrl.search = url.search;

  const iOS_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';

  const upstreamResp = await fetch(upstreamUrl.toString(), {
    headers: {
      'User-Agent': iOS_UA,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9',
    },
    redirect: 'manual',
  });

  if (upstreamResp.status >= 300 && upstreamResp.status < 400) {
    return new Response(JSON.stringify({ redirected: true, to: upstreamResp.headers.get('location') }), {
      headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*' }
    });
  }

  let html = await upstreamResp.text();
  
  // Strip ads
  html = html.replace(/<center><a href="https?:\/\/d\.[^"]*down\.php"[^>]*>.*?<\/a><\/center>/gi, '');
  html = html.replace(/<script[^>]*src="\/\/js\.users\.51\.la[^"]*"[^>]*>[\s\S]*?<\/script>/gi, '');
  html = html.replace(/<script[^>]*src='https?:\/\/www\.googletagmanager\.com[^']*'[^>]*>[\s\S]*?<\/script>/gi, '');
  html = html.replace(/<script>[\s\S]*?window\.dataLayer[\s\S]*?<\/script>/gi, '');
  html = html.replace(/<span style="display:none">\s*<script[\s\S]*?<\/span>/gi, '');

  const headers = new Headers(upstreamResp.headers);
  headers.set('access-control-allow-origin', '*');
  headers.delete('x-frame-options');
  headers.delete('content-security-policy');

  return new Response(html, { status: upstreamResp.status, headers });
}
