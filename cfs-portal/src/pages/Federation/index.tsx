import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import FederationGrid from "../../components/FederationGrid";

const FederationInstances = () => {
    return (
      <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb='20px'>
              <Typography fontWeight='400' variant="h4">
                  Federation
              </Typography>
          </Box>
          <Box>
              <FederationGrid />
          </Box>
      </>
    );
};

export default FederationInstances;
