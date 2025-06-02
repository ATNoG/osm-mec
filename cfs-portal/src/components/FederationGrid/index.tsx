import { useState, useEffect, useMemo } from "react"
import Box from "@mui/material/Box"
import { Button, Tooltip, Skeleton } from "@mui/material"
import AddCircleIcon from "@mui/icons-material/AddCircle"
import ConfirmationDialog from "../../components/Dialog/ConfirmationDialog"
import FormDialog from "../../components/Dialog/FormDialog"
import DropdownButton from "../../components/DropdownButton"
import { ActionType, FederationStatus, Item, type DropdownOption, type FormDialogField } from "../../types/Component"
import toast from "../../utils/toast"
import { getFederations, createFederation, deleteFederation } from "../../api/api"
import Typography from "@mui/material/Typography";
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import StopCircleIcon from '@mui/icons-material/StopCircle';

import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table';

const renderFederationStatus = (status: FederationStatus) => {
  switch (status) {
    case FederationStatus.SUCCESS:
      return <CheckCircleIcon color='success' />
    case FederationStatus.FAILED:
      return <CancelIcon color='error' />
    default:
      return <StopCircleIcon sx={{ color: '#aaa' }} />;
  }
}

const FederationGrid = () => {
  const [federations, setFederations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true)
  const [isFormDialogOpen, setIsFormDialogOpen] = useState(false)
  const [isConfirmationDialogOpen, setIsConfirmationDialogOpen] = useState(false)
  const [selectedFederationId, setSelectedFederationId] = useState("")

  // Get Federations Data each 5 seconds
  useEffect(() => {
    const fetchData = async () => {
      fetchFederations();
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);


  const fetchFederations = async () => {
    try {
      const { data }: any = await getFederations()
      setFederations(data)
    } catch (error) {
      toast.error("Error fetching federations")
      setFederations([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreateFederation = async (formData: any) => {
    try {
      await createFederation(formData)
      toast.success("Federation created successfully")
      fetchFederations()
    } catch (error) {
      toast.error("Error creating federation")
    }
  }

  const handleDeleteFederation = async () => {
    try {
      await deleteFederation(selectedFederationId)
      toast.success("Federation deleted successfully")
      fetchFederations()
      setIsConfirmationDialogOpen(false)
    } catch (error) {
      toast.error("Error deleting federation")
    }
  }

  const openConfirmationDialog = (id: any) => {
    setSelectedFederationId(id)
    setIsConfirmationDialogOpen(true)
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

  const columns: MRT_ColumnDef<any>[] = [
    {
      id: 'origin', 
      header: 'Federation Origin',
      accessorKey: 'origin',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'left' as const,
          sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'left' as const,
          sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => (
          <Tooltip title={ row.original.origin }>
              <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                  {row.original.origin}
              </Typography>
          </Tooltip>
      ),
    },
    {
      id: 'partner',
      header: 'Federation Partner',
      accessorKey: 'partner',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'left' as const,
          sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'left' as const,
          sx: { minWidth: '300px', Width: '300px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => (
          <Tooltip title={ row.original.partner }>
              <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                  {row.original.partner}
              </Typography>
          </Tooltip>
      ),
    },
    {
      id: 'applications',
      header: '# Apps',
      accessorKey: 'number_applications',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '100px', Width: '100px', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => (
          <Tooltip title={ row.original.number_applications }>
              <Typography variant="body2" noWrap sx={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                  {row.original.number_applications}
              </Typography>
          </Tooltip>
      ),
    },
    {
      accessorKey: 'initial_date',
      header: 'Initial Date',
      id: 'initial_date',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => {
          const rawDate = row.original['initial_date'];
          if (!rawDate) {
              return (
                  <Typography variant="body2" textAlign="center">
                      -
                  </Typography>
              );  
          }
          const date = new Date(rawDate);
          return (
              <Tooltip title={date.toLocaleString('en-GB')}>
                  <Typography variant="body2">
                      {date.toLocaleDateString('en-GB')}
                  </Typography>
              </Tooltip>
          );
      }                
    },
    {
      accessorKey: 'expiry_date',
      header: 'Expiry Date',
      id: 'expiry_date',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => {
          const rawDate = row.original['expiry_date'];
          if (!rawDate) {
              return (
                  <Typography variant="body2" textAlign="center">
                      -
                  </Typography>
              );  
          }
          const date = new Date(rawDate);
          return (
              <Tooltip title={date.toLocaleString('en-GB')}>
                  <Typography variant="body2">
                      {date.toLocaleDateString('en-GB')}
                  </Typography>
              </Tooltip>
          );
      }                
    },
    {
      accessorKey: 'renewal_date',
      header: 'Renewal Date',
      id: 'renewal_date',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '120px', Width: '120px', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => {
          const rawDate = row.original['renewal_date'];
          if (!rawDate) {
              return (
                  <Typography variant="body2" textAlign="center">
                      -
                  </Typography>
              );  
          }
          const date = new Date(rawDate);
          return (
              <Tooltip title={date.toLocaleString('en-GB')}>
                  <Typography variant="body2">
                      {date.toLocaleDateString('en-GB')}
                  </Typography>
              </Tooltip>
          );
      }                
    },
    {
      id: 'status', 
      header: 'Status',
      accessorKey: 'status',
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
        align: 'center' as const,
        sx: { minWidth: '80px', Width: '80px', maxWidth: '80px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
        align: 'center' as const,
        sx: { minWidth: '80px', Width: '80px', maxWidth: '80px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => {
        const status: FederationStatus = row.original.status ? FederationStatus.SUCCESS : FederationStatus.FAILED;
        return (
          status !== undefined && status !== null ? (
            <Tooltip title={status}>
              {renderFederationStatus(status as FederationStatus)}
            </Tooltip>
            ) : (
            <Typography variant="body2" textAlign='center'>
                -
            </Typography>
          )
        );
      },
    },
    {
      id: "actions",
      accessorKey: "actions",
      headerName: "Actions",
      enableSorting: false,
      enableColumnActions: false,
      muiTableHeadCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '70px', Width: '70px', maxWidth: '70px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      muiTableBodyCellProps: () => ({
          align: 'center' as const,
          sx: { minWidth: '70px', Width: '70px', maxWidth: '70px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'},
      }),
      Cell: ({ row }: any) => (
        <DropdownButton
          options={
            [
              {
                label: "Delete",
                handleClick: () => openConfirmationDialog(row.original.id),
              },
            ] as DropdownOption[]
          }
        />
      ),
    },
  ]

    const rootData = useMemo(() => federations, [federations]);
    const table = useMaterialReactTable({
        columns,
        data: rootData,
        // getSubRows: (row: RowData) => instanceData.filter((r: RowData) => r.appiId === row.id),
        paginateExpandedRows: false,

        enableExpandAll: false, //hide expand all double arrow in column header
        enableExpanding: false, //disable expanding rows by default (replaced by a custom expand function)

        enableDensityToggle: false,
        initialState: { density: 'compact' },

        enableFullScreenToggle: false,
    });

  return (
    <>
        {loading ? (
            // Show a loading skeleton while data is being fetched
            <Box sx={{ width: '100%' }}>
                <Skeleton variant="rectangular" width="100%" height={200} />
                <Skeleton variant="text" width="100%" />
                <Skeleton variant="text" width="100%" />
                <Skeleton variant="text" width="100%" />
            </Box>
        ) : (
            <MaterialReactTable table={table} />
        )}
        
        <FormDialog
            open={isFormDialogOpen}
            onClose={() => setIsFormDialogOpen(false)}
            onSubmit={handleCreateFederation}
            title="Add New Federation"
            fields={formFields}
        />
        <ConfirmationDialog
            open={isConfirmationDialogOpen}
            onClose={() => setIsConfirmationDialogOpen(false)}
            onConfirm={handleDeleteFederation}
            action={ActionType.DELETE}
            item={Item.FEDERATION}
        />
    </>
  );
}

export default FederationGrid;
