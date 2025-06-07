# HireCJ Homepage

A LinkedIn-style profile landing page for HireCJ - an AI-powered customer support agent that handles customer inquiries autonomously.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- **Backend API server running on port 8000** (see hirecj-agents README)

### Installation

```bash
# Clone the repository
git clone [your-repo-url]
cd hirecj-homepage

# Install dependencies
npm install
```

### Running the Application

**IMPORTANT: The backend API server must be running first!**

```bash
# First, start the backend API (in hirecj-agents directory):
cd ../hirecj-agents
make dev

# Then start the frontend development server:
cd ../hirecj-homepage
npm run dev

# The app will be available at http://localhost:3456

# If you're experiencing caching issues (changes not appearing):
npm run dev:clean
```

### Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## 🔧 Configuration

### Port Configuration
By default, the application runs on port **3456**. You can change this by setting the `PORT` environment variable:

```bash
PORT=8080 npm run dev
```

## 📁 Project Structure

```
hirecj-homepage/
├── client/                 # React frontend
│   ├── public/            # Static assets
│   └── src/               # Source code
│       ├── components/    # React components
│       ├── hooks/         # Custom React hooks
│       ├── lib/           # Utility libraries
│       └── pages/         # Page components
├── server/                # Express backend
│   ├── index.ts          # Server entry point
│   ├── routes.ts         # API routes
│   └── storage.ts        # Data storage logic
├── shared/               # Shared types and schemas
├── attached_assets/      # Project assets and documentation
└── public/              # Public static files
```

## 🎨 Features

- **Interactive Profile Page**: LinkedIn-style layout showcasing HireCJ's capabilities
- **Live Chat Demo**: Interactive chat interface demonstrating HireCJ's conversational abilities
- **WebSocket Integration**: Real-time communication with the backend API server
- **Progress Updates**: Visual feedback while CJ is processing responses
- **Daily Reports**: Visual representation of HireCJ's performance metrics
- **Responsive Design**: Fully responsive design that works on all devices
- **Modern Stack**: Built with React, TypeScript, Tailwind CSS, and Express

## 🔐 User Identity Management

**IMPORTANT: Frontend NEVER generates user IDs - this is backend's responsibility**

### What Frontend Does
1. **Stores** raw merchant data in localStorage:
   - `merchantId`: The merchant's identifier (e.g., "merchant_cratejoy-dev")
   - `shopDomain`: The Shopify domain (e.g., "cratejoy-dev.myshopify.com")

2. **Sends** this data to backend via WebSocket `session_update`:
   ```javascript
   // ✅ CORRECT - Frontend sends raw data only
   const sessionUpdate = {
     type: 'session_update',
     data: {
       merchant_id: localStorage.getItem('merchantId'),
       shop_domain: localStorage.getItem('shopDomain')
       // NO user_id field!
     }
   };
   ```

### What Frontend MUST NOT Do
```javascript
// ❌ WRONG - Never generate IDs in frontend
const userId = `shop_${shopDomain.replace('.myshopify.com', '')}`;  // NO!
const userId = generateUserId(shopDomain);  // NO!
const userId = hashShopDomain(shopDomain);  // NO!
```

### Why This Matters
- User IDs must be consistent across all services
- Backend uses SHA256-based generation (`usr_xxxxxxxx` format)
- Frontend-generated IDs cause database foreign key violations
- Single Source of Truth: Backend is the authority

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Backend**: Express.js, TypeScript
- **UI Components**: Radix UI, shadcn/ui
- **Animations**: Framer Motion
- **HTTP Client**: Tanstack Query
- **Styling**: Tailwind CSS with custom animations

## 📜 Available Scripts

- `npm run dev` - Start development server (port 3456)
- `npm run build` - Build for production
- `npm start` - Run production server
- `npm run check` - Run TypeScript type checking
- `npm run db:push` - Push database schema changes (if using Drizzle)

## 🔒 Environment Variables

Create a `.env` file in the root directory to configure environment variables:

```env
PORT=3456                  # Server port (optional, defaults to 3456)
NODE_ENV=development       # Environment mode
API_URL=ws://localhost:8000 # Backend API WebSocket URL (optional, defaults to ws://localhost:8000)
```

## 🐛 Troubleshooting

### Frontend changes not updating after restart

If you're experiencing issues where JavaScript changes aren't reflected after restarting with `npm run dev`, this is due to Vite's dependency pre-bundling cache. Use our clean development script:

```bash
npm run dev:clean
```

This will clear Vite's cache and ensure you get the latest changes. The issue typically occurs when:
- Dependencies are updated
- Major refactoring is done
- Switching between branches with different dependencies

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please open an issue in the GitHub repository or contact the development team.

---

Built with ❤️ for HireCJ - Your AI Customer Support Agent