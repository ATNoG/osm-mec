import React, { useRef, useState } from "react";
import AddCircleIcon from "@mui/icons-material/AddCircle"
import Box from "@mui/material/Box";
import { Button } from "@mui/material"
import Typography from "@mui/material/Typography";
import FederationGrid from "../../components/FederationGrid";
import FormDialog from "../../components/Dialog/FormDialog"
import { type FormDialogField } from "../../types/Component"
import { createFederation } from "../../api/api"
import toast from "../../utils/toast"

const FederationInstances = () => {
    const [isFormDialogOpen, setIsFormDialogOpen] = useState(false)

    const federationGridRef = useRef<{ fetchFederations: () => void }>(null)

    const handleCreateFederation = async (formData: any) => {
        try {
            await createFederation(formData)
            toast.success("Federation created successfully")
            federationGridRef.current?.fetchFederations()
        } catch (error) {
            toast.error("Error creating federation")
        }
    }

    const formFields: FormDialogField[] = [
        {
          id: "federation_endpoint",
          label: "Federation Endpoint",
          type: "text",
          required: true,
          validate: (value: string) => {
            try {
              new URL(value);
              return true;
            } catch (_) {
              return "Please enter a valid URL.";
            }
          },
        },
        {
          id: "authentication_endpoint",
          label: "Authentication Endpoint",
          type: "text",
          required: true,
        },
        {
          id: "client_id",
          label: "Client ID",
          type: "text",
          required: true,
        },
        {
          id: "client_secret",
          label: "Client Secret",
          type: "text",
          required: true,
        },
      ]

    return (
        <>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb='20px'>
                <Typography fontWeight='400' variant="h4">
                    Federation
                </Typography>
                <Button variant="contained" color="primary" startIcon={<AddCircleIcon />} onClick={() => setIsFormDialogOpen(true)}>
                    Add Federation
                </Button>
            </Box>

            <Box>
                <FederationGrid ref={federationGridRef} />
            </Box>

            <FormDialog
                open={isFormDialogOpen}
                onClose={() => setIsFormDialogOpen(false)}
                onSubmit={handleCreateFederation}
                title="Add New Federation"
                fields={formFields}
            />
        </>
    );
};

export default FederationInstances;
