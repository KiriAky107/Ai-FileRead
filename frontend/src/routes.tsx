import { createBrowserRouter, Navigate } from 'react-router-dom';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Documents from '@/pages/Documents';
import FormFill from '@/pages/FormFill';
import Assistant from '@/pages/Assistant';
import ExcelParse from '@/pages/ExcelParse';
import MainLayout from '@/components/layouts/MainLayout';
import { RouteGuard } from '@/components/common/RouteGuard';

export const routes = [
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <RouteGuard>
        <MainLayout />
      </RouteGuard>
    ),
    children: [
      {
        path: '/',
        element: <Dashboard />,
      },
      {
        path: '/documents',
        element: <Documents />,
      },
      {
        path: '/form-fill',
        element: <FormFill />,
      },
      {
        path: '/assistant',
        element: <Assistant />,
      },
      {
        path: '/excel-parse',
        element: <ExcelParse />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
