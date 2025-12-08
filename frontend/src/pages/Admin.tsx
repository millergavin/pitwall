import { useState } from 'react';
import { PageLayout } from '../components/PageLayout';
import { DatabaseAdmin } from '../components/DatabaseAdmin';

export const Admin = () => {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === 'pitwall') {
      setIsAuthenticated(true);
    } else {
      alert('Incorrect password');
      setPassword('');
    }
  };

  if (!isAuthenticated) {
    return (
      <PageLayout pageTitle="Admin">
        <div className="max-w-md mx-auto mt-20">
          <div className="bg-black rounded-corner p-8">
            <h2 className="text-white text-xl f1-display-bold mb-6">Database Admin Access</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="password" className="block text-zinc-400 text-sm mb-2">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-corner text-white focus:outline-none focus:ring-2 focus:ring-f1-red"
                  placeholder="Enter password"
                  autoFocus
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-4 bg-f1-red text-white rounded-corner hover:bg-[#981b1b] transition-colors f1-display-bold text-sm"
              >
                ACCESS
              </button>
            </form>
            <p className="text-zinc-600 text-xs mt-4 text-center">
              This protects against accidental access
            </p>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout pageTitle="Admin">
      <div className="max-w-3xl mx-auto">
        <DatabaseAdmin />
      </div>
    </PageLayout>
  );
};

