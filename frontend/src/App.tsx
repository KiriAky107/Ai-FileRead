import { RouterProvider } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { TemplateFillProvider } from '@/context/TemplateFillContext';
import { router } from '@/routes';
import { Toaster } from 'sonner';

function App() {
  return (
    <AuthProvider>
      <TemplateFillProvider>
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors closeButton />
      </TemplateFillProvider>
    </AuthProvider>
  );
}

export default App;
