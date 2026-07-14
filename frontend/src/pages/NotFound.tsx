import { Link } from 'react-router-dom';
import { Button, Card } from '../components/UI';
export default function NotFound(){return <Card className="settings-card" style={{textAlign:'center',marginTop:60}}><h1>Page not found</h1><p className="muted">The requested page does not exist.</p><Link to="/"><Button>Back to Dashboard</Button></Link></Card>}
