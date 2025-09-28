# PaperIgnition Web Application

## Production Deployment

### Ubuntu Nginx Setup

1. **Install Nginx (if not already installed):**
   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. **Copy your project files to Ubuntu:**
   ```bash
   # Example: copy to /root/PaperIgnition/beta_frontend/
   # Your files should include index.html, js/, css/, etc.
   ```

3. **Set proper permissions:**
   ```bash
   chmod 755 /root
   chmod -R 755 /root/PaperIgnition/
   ```

4. **Copy nginx configuration:**
   ```bash
   sudo cp /root/PaperIgnition/beta_frontend/nginx.conf /etc/nginx/sites-available/paperignition
   ```

5. **Enable the site:**
   ```bash
   # Remove default site
   sudo rm /etc/nginx/sites-enabled/default

   # Enable your site
   sudo ln -s /etc/nginx/sites-available/paperignition /etc/nginx/sites-enabled/
   ```

6. **Test configuration:**
   ```bash
   sudo nginx -t
   ```

7. **Start/restart nginx:**
   ```bash
   sudo systemctl restart nginx
   sudo systemctl enable nginx  # Enable on boot
   ```

8. **Check status:**
   ```bash
   sudo systemctl status nginx
   ```
