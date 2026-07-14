import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import Quotations from './pages/Quotations';
import CreateQuotation from './pages/CreateQuotation';
import QuotationDetails from './pages/QuotationDetails';
import Invoices from './pages/Invoices';
import InvoiceDetails from './pages/InvoiceDetails';
import Payments from './pages/Payments';
import Followups from './pages/Followups';
import Catalog from './pages/Catalog';
import Reports from './pages/Reports';
import SettingsPage from './pages/SettingsPage';
import NotFound from './pages/NotFound';

export default function App(){return <Routes><Route element={<Layout/>}><Route path="/" element={<Dashboard/>}/><Route path="/customers" element={<Customers/>}/><Route path="/quotations" element={<Quotations/>}/><Route path="/quotations/new" element={<CreateQuotation/>}/><Route path="/quotations/:id/edit" element={<CreateQuotation/>}/><Route path="/quotations/:id" element={<QuotationDetails/>}/><Route path="/invoices" element={<Invoices/>}/><Route path="/invoices/:id" element={<InvoiceDetails/>}/><Route path="/payments" element={<Payments/>}/><Route path="/followups" element={<Followups/>}/><Route path="/catalog" element={<Catalog/>}/><Route path="/reports" element={<Reports/>}/><Route path="/settings" element={<SettingsPage/>}/><Route path="*" element={<NotFound/>}/></Route></Routes>}
