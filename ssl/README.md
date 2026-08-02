# SSL Certificates

Place your SSL certificate and private key in this directory for production HTTPS:

- `erpmini.crt` - Your SSL certificate
- `erpmini.key` - Your SSL private key

## Self-Signed Certificate (Development/Testing)

Generate a self-signed certificate for testing:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout erpmini.key \
  -out erpmini.crt \
  -subj "/C=VN/ST=Ho Chi Minh/L=Ho Chi Minh/O=ERP-VIET/CN=localhost"
```

## Let's Encrypt (Production)

For production, use Let's Encrypt:

```bash
certbot certonly --standalone -d your-domain.com
```

Then copy the certificates to this directory.
