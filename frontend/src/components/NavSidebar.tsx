import { NavMenuItem } from './NavMenuItem';

export const NavSidebar = () => {
  return (
    <div className="p-2 pt-6">
      <nav className="space-y-1">
        <NavMenuItem to="/">Dashboard</NavMenuItem>
        <NavMenuItem to="/championship">Championship</NavMenuItem>
        <NavMenuItem to="/circuits">Circuits</NavMenuItem>
        <NavMenuItem to="/grand-prix">Grand Prix</NavMenuItem>
        <NavMenuItem to="/drivers">Drivers</NavMenuItem>
        <NavMenuItem to="/teams">Teams</NavMenuItem>
      </nav>
    </div>
  );
};

