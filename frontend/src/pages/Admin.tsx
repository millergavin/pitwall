import { PageLayout } from '../components/PageLayout';
import { DatabaseAdmin } from '../components/DatabaseAdmin';

export const Admin = () => {
  return (
    <PageLayout pageTitle="Admin">
      <div className="max-w-3xl mx-auto">
        <DatabaseAdmin />
      </div>
    </PageLayout>
  );
};

