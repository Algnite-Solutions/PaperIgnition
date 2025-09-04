# PaperIgnition Web Application

A modern, AlphaXiv-inspired web application for academic paper discovery and recommendation.

## Features

- **Clean, Modern Design** - Inspired by AlphaXiv with a focus on readability and user experience
- **Responsive Layout** - Works seamlessly on desktop and mobile devices  
- **Paper Discovery** - Browse and search academic papers with intelligent filtering
- **Bookmarking** - Save interesting papers for later reading
- **Paper Details** - View full paper abstracts, metadata, and content
- **Search Functionality** - Real-time search across titles, authors, abstracts, and tags
- **Dark Mode Support** - Toggle between light and dark themes (Ctrl+D)

## Design Philosophy

The application follows AlphaXiv's design principles:

- **Minimalist Interface** - Clean, uncluttered design focusing on content
- **Typography** - Uses Noto Sans and Rubik fonts for excellent readability
- **Color Scheme** - Neutral palette with subtle red accents
- **Information Density** - Maximizes useful information while maintaining clarity
- **Responsive First** - Mobile-friendly design that scales beautifully

## Quick Start

### Option 1: Python Server (Recommended)
```bash
cd web/
python server.py
```
Then open http://localhost:3000 in your browser.

### Option 2: Any HTTP Server
```bash
# Using Python 3
python -m http.server 3000

# Using Node.js (if you have http-server installed)
npx http-server -p 3000

# Using PHP
php -S localhost:3000
```

## File Structure

```
web/
├── index.html          # Main application page
├── paper.html          # Paper detail page
├── js/
│   └── main.js        # Application JavaScript
├── server.py          # Simple Python server
└── README.md          # This file
```

## Usage

### Main Features

1. **Browse Papers** - The home page displays a list of academic papers with thumbnails, titles, authors, abstracts, and metadata
2. **Search** - Use the search bar to find papers by title, author, abstract, or tags
3. **View Details** - Click on any paper card to view the full paper details
4. **Bookmark Papers** - Click the bookmark button to save papers (stored in localStorage)
5. **Responsive Design** - The layout adapts to different screen sizes

### Navigation

- **Home** - Main paper listing page
- **Paper Detail** - Individual paper view with full content
- **Bookmarks** - Saved papers (persistent across sessions)

### Keyboard Shortcuts

- `Ctrl+D` - Toggle dark/light theme

## Customization

### Adding New Papers

Edit the `samplePapers` array in `js/main.js`:

```javascript
const samplePapers = [
    {
        id: 'unique-id',
        title: 'Paper Title',
        authors: ['Author 1', 'Author 2'],
        abstract: 'Paper abstract...',
        tags: ['Tag1', 'Tag2'],
        submittedDate: 'Date',
        publishDate: 'Date',
        comments: 'Publication info',
        thumbnail: 'Short description'
    }
    // Add more papers...
];
```

### Styling

The application uses CSS custom properties (variables) for easy theming. Main variables are defined in `:root`:

```css
:root {
    --bg-color: #ffffff;
    --text-primary: #1a1a1a;
    --text-secondary: #666666;
    --accent-red: #dc2626;
    /* ... more variables */
}
```

### API Integration

To connect to a real backend API, update the `PaperService` class methods in `main.js` to make actual HTTP requests instead of returning sample data.

## Browser Support

- Modern browsers with ES6+ support
- Chrome, Firefox, Safari, Edge (latest versions)
- Responsive design works on mobile browsers

## Development

The application is built with vanilla JavaScript and CSS for simplicity and performance. No build process or dependencies are required.

### Local Development

1. Clone/download the files
2. Run `python server.py` 
3. Open http://localhost:3000
4. Make changes to HTML, CSS, or JavaScript files
5. Refresh the browser to see changes

## Production Deployment

For production deployment:

1. Serve the files from any web server (Apache, Nginx, etc.)
2. Update API endpoints in `main.js` to point to your backend
3. Consider adding proper error handling and loading states
4. Implement authentication if required
5. Add analytics and monitoring

## License

This project is part of the PaperIgnition platform. See the main project documentation for license information.