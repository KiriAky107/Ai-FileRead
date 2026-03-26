import { createBrowserRouter, Navigate } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';
import Documents from '@/pages/Documents';
import TemplateFill from '@/pages/TemplateFill';
import InstructionChat from '@/pages/InstructionChat';
import TaskHistory from '@/pages/TaskHistory';
import MainLayout from '@/components/layouts/MainLayout';

export const routes = [
  {
    path: '/',
    element: <MainLayout />,
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
        element: <TemplateFill />,
      },
      {
        path: '/assistant',
        element: <InstructionChat />,
      },
      {
        path: '/task-history',
        element: <TaskHistory />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
