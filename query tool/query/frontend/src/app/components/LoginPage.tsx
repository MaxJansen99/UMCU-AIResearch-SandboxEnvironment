import { FormEvent, useState } from 'react';
import { AlertCircle, LogIn } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { login, routeForRole, storeToken } from '../utils/authClient';
import huLogo from '../../assets/hogeschool_utrecht_Logo_jpg.png';
import umcLogo from '../../assets/umc_utrecht_Logo_jpg.svg';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const result = await login(username, password);
      storeToken(result.token);
      window.location.assign(routeForRole(result.user.role));
    } catch {
      setError('Verkeerde inloggegevens.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="relative max-w-[960px] mx-auto px-6 py-5 text-center">
          <img src={umcLogo} alt="UMC Utrecht" className="mx-auto mb-3 h-14 w-auto object-contain" />
          <h1 className="text-2xl font-bold text-gray-900">DICOM Metadata Query</h1>
          <p className="text-sm text-gray-600 mt-1">Log in met je demo account</p>
        </div>
      </header>

      <main className="mx-auto flex max-w-[480px] flex-col px-6 py-10">
        <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-gray-900">Inloggen</h2>
            <p className="text-sm text-gray-600">Gebruik je researcher of datamanager account.</p>
          </div>

          {error && (
            <div className="mt-5 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Gebruikersnaam</Label>
              <Input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Wachtwoord</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
          </div>

          <Button type="submit" className="mt-6 w-full" disabled={isSubmitting}>
            <LogIn className="h-4 w-4" />
            {isSubmitting ? 'Inloggen...' : 'Inloggen'}
          </Button>
        </form>

        <div className="mt-8 flex items-center justify-center gap-3">
          <span className="text-xs font-medium uppercase text-gray-500">Made by</span>
          <img src={huLogo} alt="Hogeschool Utrecht" className="h-16 w-auto object-contain" />
        </div>
      </main>
    </div>
  );
}
